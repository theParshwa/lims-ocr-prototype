"""
processing.py - Job status polling and data retrieval endpoints.

GET    /api/jobs                   - List all jobs
GET    /api/jobs/{job_id}          - Get job status and full extraction result
PUT    /api/jobs/{job_id}/data     - Update (edit) extracted data + capture corrections
POST   /api/jobs/{job_id}/reprocess - Reprocess from scratch
DELETE /api/jobs/{job_id}          - Delete job and associated files
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db
from models.lims_models import LIMSJob, CorrectionExample
from models.schemas import ExtractionResult, JobStatus

router = APIRouter(prefix="/api/jobs", tags=["processing"])
logger = logging.getLogger(__name__)


@router.get("", summary="List all processing jobs")
async def list_jobs(
    db: AsyncSession = Depends(get_db),
    limit: int = 50,
    offset: int = 0,
):
    result = await db.execute(
        select(LIMSJob).order_by(LIMSJob.created_at.desc()).offset(offset).limit(limit)
    )
    jobs = result.scalars().all()
    return {"jobs": [_job_summary(j) for j in jobs], "total": len(jobs)}


@router.get("/{job_id}", summary="Get job status and extraction data")
async def get_job(job_id: str, db: AsyncSession = Depends(get_db)):
    job = await _get_job_or_404(job_id, db)
    return {
        **_job_summary(job),
        "result": job.get_result(),
        "error_message": job.error_message,
    }


@router.put("/{job_id}/data", summary="Update extracted data and capture corrections")
async def update_job_data(
    job_id: str,
    payload: dict,
    db: AsyncSession = Depends(get_db),
):
    """
    Persist user edits.  Diffs original vs updated, saves every changed
    field as a CorrectionExample and embeds it for future RAG retrieval.
    """
    job = await _get_job_or_404(job_id, db)

    if job.status not in (JobStatus.COMPLETE.value, JobStatus.VALIDATING.value):
        raise HTTPException(status_code=409, detail=f"Cannot edit job in state '{job.status}'")

    try:
        updated = ExtractionResult(**payload)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid data structure: {exc}") from exc

    # ── Capture corrections ────────────────────────────────────────────────────
    original_raw = job.get_result() or {}
    corrections  = _diff_results(original_raw, payload, job.document_type or "")
    if corrections:
        asyncio.create_task(_persist_corrections(db, job_id, corrections))

    # ── Re-run validation ──────────────────────────────────────────────────────
    from validation.schema_validator import SchemaValidator
    from validation.cross_ref_validator import CrossRefValidator

    schema_issues = SchemaValidator().validate(updated)
    cross_issues  = CrossRefValidator().validate(updated)
    updated.validation_errors = [i.to_dict() for i in schema_issues + cross_issues]

    job.set_result(updated.model_dump())
    job.updated_at = datetime.now(timezone.utc)
    await db.commit()

    return {
        "job_id": job_id,
        "status": "updated",
        "validation_error_count": len(updated.validation_errors),
        "corrections_captured": len(corrections),
    }


@router.post("/{job_id}/reprocess", summary="Reprocess a job from scratch")
async def reprocess_job(job_id: str, background_tasks, db: AsyncSession = Depends(get_db)):
    from api.routes.upload import _process_document
    job = await _get_job_or_404(job_id, db)
    job.status         = JobStatus.PENDING.value
    job.error_message  = None
    job.result_json    = None
    await db.commit()
    background_tasks.add_task(_process_document, job_id, job.file_path, job.original_filename)
    return {"job_id": job_id, "status": "reprocessing"}


@router.get("/{job_id}/document", summary="Serve the original uploaded document file")
async def get_job_document(job_id: str, db: AsyncSession = Depends(get_db)):
    """Stream the original uploaded file back to the client."""
    import mimetypes
    from fastapi.responses import FileResponse
    from pathlib import Path

    job = await _get_job_or_404(job_id, db)
    if not job.file_path:
        raise HTTPException(status_code=404, detail="No file associated with this job")

    path = Path(job.file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")

    content_type, _ = mimetypes.guess_type(str(path))
    content_type = content_type or "application/octet-stream"

    return FileResponse(
        path=str(path),
        media_type=content_type,
        filename=job.original_filename or path.name,
        headers={"Content-Disposition": f'inline; filename="{job.original_filename or path.name}"'},
    )


@router.delete("/{job_id}", summary="Delete a job and its files")
async def delete_job(job_id: str, db: AsyncSession = Depends(get_db)):
    import os
    job = await _get_job_or_404(job_id, db)
    for path in [job.file_path, job.output_path]:
        if path:
            try: os.remove(path)
            except OSError: pass
    await db.delete(job)
    await db.commit()
    return {"deleted": job_id}


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_job_or_404(job_id: str, db: AsyncSession) -> LIMSJob:
    job = await db.get(LIMSJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    return job


def _job_summary(job: LIMSJob) -> dict:
    return {
        "job_id":        job.id,
        "filename":      job.original_filename,
        "status":        job.status,
        "document_type": job.document_type,
        "created_at":    job.created_at.isoformat() if job.created_at else None,
        "updated_at":    job.updated_at.isoformat() if job.updated_at else None,
        "output_path":   job.output_path,
    }


# ── Correction capture ────────────────────────────────────────────────────────

# Sheet keys that hold lists of records
_SHEET_KEYS = [
    "analysis_types", "common_names", "analysis", "components", "units",
    "products", "product_specs", "customers", "instruments", "lims_users",
    "vendors", "suppliers", "process_schedules", "lists", "list_entries",
    "sampling_points", "product_grades", "sites", "plants", "suites",
    "process_units", "versions",
]

# Fields used as row identifiers per sheet
_ID_FIELDS: dict[str, list[str]] = {
    "analysis":         ["name"],
    "components":       ["analysis_name", "component_name"],
    "products":         ["product", "grade"],
    "product_specs":    ["product", "grade", "component_name"],
    "instruments":      ["instrument_name"],
    "lims_users":       ["username"],
    "analysis_types":   ["analysis_type_code"],
    "common_names":     ["name"],
    "units":            ["unit_code"],
    "customers":        ["customer_name"],
}


def _row_context(sheet_key: str, row: dict) -> str:
    """Build a short identifier string for a row."""
    id_fields = _ID_FIELDS.get(sheet_key, list(row.keys())[:2])
    parts = [f"{f}={row.get(f,'')}" for f in id_fields if row.get(f)]
    return " | ".join(parts) if parts else str(list(row.items())[:2])


def _diff_results(
    original: dict,
    updated: dict,
    document_type: str,
) -> list[dict]:
    """
    Compare two ExtractionResult dicts field-by-field.
    Returns a list of correction dicts for every changed field.
    """
    corrections = []
    for sheet_key in _SHEET_KEYS:
        orig_rows = original.get(sheet_key) or []
        upd_rows  = updated.get(sheet_key)  or []
        for i, (orig_row, upd_row) in enumerate(zip(orig_rows, upd_rows)):
            if not isinstance(orig_row, dict) or not isinstance(upd_row, dict):
                continue
            context = _row_context(sheet_key, upd_row)
            for field, upd_val in upd_row.items():
                if field in ("confidence", "source_text", "review_notes"):
                    continue
                orig_val = orig_row.get(field)
                if str(orig_val) != str(upd_val) and upd_val not in (None, ""):
                    corrections.append({
                        "sheet_name":      sheet_key,
                        "field_name":      field,
                        "original_value":  str(orig_val) if orig_val is not None else "",
                        "corrected_value": str(upd_val),
                        "context_text":    context,
                        "document_type":   document_type,
                    })
    return corrections


async def _persist_corrections(
    db: AsyncSession,
    job_id: str,
    corrections: list[dict],
) -> None:
    """Save corrections to DB and embed them for RAG retrieval."""
    try:
        from rag.retriever import store_embedding

        for c in corrections:
            # Save to DB
            ex = CorrectionExample(
                job_id          = job_id,
                document_type   = c["document_type"],
                sheet_name      = c["sheet_name"],
                field_name      = c["field_name"],
                original_value  = c["original_value"],
                corrected_value = c["corrected_value"],
                context_text    = c["context_text"],
            )
            db.add(ex)
            await db.flush()  # get ex.id

            # Embed: "{sheet} {field} {context}" as the searchable text
            embed_text = (
                f"Sheet: {c['sheet_name']} | "
                f"Field: {c['field_name']} | "
                f"Context: {c['context_text']} | "
                f"Doc type: {c['document_type']}"
            )
            await store_embedding(
                db,
                source_type = "correction",
                source_id   = str(ex.id),
                text        = embed_text,
                metadata    = c,
            )

        await db.commit()
        logger.info("Captured %d corrections for job %s", len(corrections), job_id)
    except Exception as exc:
        logger.error("Failed to persist corrections: %s", exc)
