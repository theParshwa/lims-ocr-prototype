"""
refine.py - Natural-language refinement of extracted LIMS data.

POST /api/jobs/{job_id}/refine
  Accepts a plain-English instruction describing what needs to change.
  Sends the current extraction result + instruction to GPT-4o.
  GPT returns a targeted list of field-level changes.
  Changes are applied, re-validated, persisted, and returned.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db
from models.lims_models import LIMSJob
from models.schemas import ExtractionResult, JobStatus

router = APIRouter(prefix="/api/jobs", tags=["refine"])
logger = logging.getLogger(__name__)

# Sheet keys that hold lists of records (same list used in processing.py)
_SHEET_KEYS = [
    "analysis_types", "common_names", "analysis", "components", "units",
    "products", "tph_grades", "sampling_points", "product_grades",
    "prod_grade_stages", "product_specs", "tph_item_codes",
    "tph_item_code_specs", "tph_item_code_supps", "tph_sample_plans",
    "tph_sample_plan_entries", "customers", "t_sites", "t_plants", "t_suites",
    "process_units", "proc_sched_parents", "process_schedules", "lists",
    "list_entries", "vendors", "suppliers", "instruments", "lims_users",
    "versions",
]

SYSTEM_PROMPT = """\
You are a LIMS (Laboratory Information Management System) data correction agent.

You are given:
1. A JSON snapshot of structured LIMS extraction data (30 sheets).
2. A plain-English instruction from a user describing what needs to change.

Your job is to identify exactly which records and fields need updating and return
ONLY a JSON object in this exact format — no markdown, no extra text:

{
  "changes": [
    {
      "sheet": "<sheet_key>",
      "row_index": <0-based integer>,
      "field": "<field_name>",
      "new_value": "<new value as string, or null to clear>",
      "explanation": "<one sentence explaining the change>"
    }
  ],
  "summary": "<one sentence describing all changes made>"
}

Rules:
- Only include rows/fields that must actually change.
- row_index is 0-based (first row = 0).
- new_value must always be a string (even for numbers), or null to clear the field.
- If nothing needs to change, return {"changes": [], "summary": "No changes required."}.
- sheet must be one of the known sheet keys provided in the data.
- Do not invent new rows; only modify existing ones unless the user explicitly asks to add a row.
- If the user asks to add a row, use row_index equal to the current length of that sheet's array.
"""


class RefineRequest(BaseModel):
    instruction: str


class ChangeRecord(BaseModel):
    sheet: str
    row_index: int
    field: str
    new_value: str | None
    explanation: str


class RefineResponse(BaseModel):
    changes: list[ChangeRecord]
    summary: str
    updated_result: dict


def _compact_snapshot(result_dict: dict) -> str:
    """
    Build a compact JSON snapshot of non-empty sheets only.
    Keeps token usage reasonable for large extractions.
    """
    snapshot: dict = {}
    for key in _SHEET_KEYS:
        rows = result_dict.get(key) or []
        if rows:
            snapshot[key] = rows
    return json.dumps(snapshot, separators=(",", ":"), default=str)


def _apply_changes(result_dict: dict, changes: list[ChangeRecord]) -> dict:
    """Apply a list of field-level changes to the result dict in-place."""
    for change in changes:
        sheet = change.sheet
        if sheet not in _SHEET_KEYS:
            logger.warning("Ignoring change for unknown sheet: %s", sheet)
            continue

        rows: list = result_dict.get(sheet) or []
        idx = change.row_index

        if idx == len(rows):
            # User requested a new row — append a blank one
            rows.append({})
            result_dict[sheet] = rows

        if idx < 0 or idx >= len(rows):
            logger.warning("row_index %d out of range for sheet %s (len=%d)", idx, sheet, len(rows))
            continue

        row = dict(rows[idx])
        val = change.new_value

        # Coerce numeric strings back to numbers if the original field was numeric
        original = row.get(change.field)
        if val is not None and isinstance(original, (int, float)):
            try:
                val = float(val) if "." in val else int(val)
            except (ValueError, TypeError):
                pass

        row[change.field] = val
        rows[idx] = row

    return result_dict


@router.post("/{job_id}/refine", response_model=RefineResponse, summary="Refine extracted data via natural language")
async def refine_job(
    job_id: str,
    body: RefineRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Accept a plain-English instruction, ask GPT to produce targeted field-level
    changes, apply them to the current extraction result, re-validate, and save.
    """
    from extraction.llm_factory import get_llm
    from langchain_core.messages import HumanMessage, SystemMessage
    from validation.schema_validator import SchemaValidator
    from validation.cross_ref_validator import CrossRefValidator

    # ── Load job ──────────────────────────────────────────────────────────────
    job: LIMSJob | None = await db.get(LIMSJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    if job.status not in (JobStatus.COMPLETE.value, JobStatus.VALIDATING.value):
        raise HTTPException(status_code=409, detail=f"Cannot refine job in state '{job.status}'")

    result_dict: dict = job.get_result() or {}
    if not result_dict:
        raise HTTPException(status_code=409, detail="Job has no extraction result to refine")

    # ── Build LLM prompt ──────────────────────────────────────────────────────
    snapshot = _compact_snapshot(result_dict)
    user_message = (
        f"Current LIMS extraction data:\n{snapshot}\n\n"
        f"User instruction: {body.instruction}"
    )

    llm = get_llm()
    logger.info("Refining job %s — instruction: %s", job_id, body.instruction[:120])

    response = llm.invoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_message),
    ])

    raw = response.content.strip()

    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        gpt_out = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("GPT returned non-JSON: %s", raw[:300])
        raise HTTPException(status_code=502, detail=f"AI returned malformed response: {exc}") from exc

    changes = [ChangeRecord(**c) for c in gpt_out.get("changes", [])]
    summary = gpt_out.get("summary", "")

    # ── Apply changes ─────────────────────────────────────────────────────────
    result_dict = _apply_changes(result_dict, changes)

    # ── Re-validate ───────────────────────────────────────────────────────────
    try:
        updated = ExtractionResult(**result_dict)
    except Exception:
        updated = ExtractionResult.model_validate(result_dict)

    schema_issues = SchemaValidator().validate(updated)
    cross_issues = CrossRefValidator().validate(updated)
    updated.validation_errors = [i.to_dict() for i in schema_issues + cross_issues]

    # ── Persist ───────────────────────────────────────────────────────────────
    job.set_result(updated.model_dump())
    job.updated_at = datetime.now(timezone.utc)
    await db.commit()

    logger.info("Refined job %s — %d change(s): %s", job_id, len(changes), summary)

    return RefineResponse(
        changes=changes,
        summary=summary,
        updated_result=updated.model_dump(),
    )
