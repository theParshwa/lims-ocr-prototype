"""
agent.py - REST endpoints for AI agent configuration.

GET  /api/agent/prompts          — get all agent prompts
PUT  /api/agent/prompts/{key}    — update a specific agent prompt
GET  /api/agent/prompts/{key}    — get a specific agent prompt
POST /api/agent/prompts/{key}/reset — reset prompt to default
GET  /api/agent/prompts/preview  — get prompts rendered with current config context
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/agent", tags=["agent"])

AGENT_CONFIG_PATH = Path(__file__).parent.parent.parent / "agent_config.json"
APP_CONFIG_PATH   = Path(__file__).parent.parent.parent / "app_config.json"

# ── Default prompts ────────────────────────────────────────────────────────────
#
# Placeholders available at runtime:
#   {lims_system}         — e.g. "LabWare", "LabVantage", "Veeva"
#   {document_type}       — e.g. "STP", "PTP", "SPEC"
#   {load_sheet_template} — pasted template from Configure › Load Sheet Template
#   {training_context}    — few-shot examples from Training tab
#   {text}                — raw document text / chunk

DEFAULT_PROMPTS: dict[str, dict] = {

    # ── 1. Classifier ─────────────────────────────────────────────────────────
    "classifier": {
        "key": "classifier",
        "name": "Document Classifier Agent",
        "description": (
            "Classifies incoming laboratory documents by type "
            "(STP, PTP, SPEC, METHOD, SOP, OTHER) with LIMS-awareness."
        ),
        "system": """\
You are an expert laboratory document analyst specialising in pharmaceutical and \
industrial LIMS implementations.

TARGET LIMS SYSTEM: {lims_system}

Your task is to classify the type of laboratory document and extract high-level \
hints that will guide downstream data-extraction agents.

DOCUMENT TYPE DEFINITIONS
─────────────────────────
• STP  (Standard Test Procedure)
      Describes HOW a test is performed — step-by-step instructions, reagent \
preparations, instrument settings, acceptance criteria.
      Key signals: "procedure", "method", "reagents", "equipment", "step", \
"pipette", "calibration", numbered steps, table of reagents.

• PTP  (Product Test Plan / Production Test Protocol)
      Defines WHAT tests are performed on a product and WHEN.
      Key signals: "test plan", "sampling plan", "release testing", "in-process", \
"test list", "schedule", "frequency", product name + test list table.

• SPEC (Product Specification)
      States the ACCEPTANCE CRITERIA for a product — min/max limits, target values.
      Key signals: "specification", "limit", "acceptance criteria", "not less than", \
"not more than", "NLT", "NMT", table of parameters with limits.

• METHOD (Analytical Method / Compendial Method)
      A validated or compendial analytical procedure (USP, EP, BP, ICH).
      Key signals: "analytical method", "USP", "EP", "BP", "compendial", \
"validated", "LOD", "LOQ", "linearity", "precision", "accuracy".

• SOP  (Standard Operating Procedure)
      General operational instructions not tied to a specific test.
      Key signals: "SOP", "operating procedure", "responsibility", "scope", \
"purpose", numbered sections without reagent tables.

• OTHER — anything that does not fit the above.

LIMS-SPECIFIC HINTS
───────────────────
LabWare  : Look for references to Analysis Types (CHEMICAL / INSTRUMENT / MICRO), \
COMPONENT tables, PRODUCT / GRADE codes, Process Schedule numbers.
LabVantage: Look for Test Definitions, Sample Login Groups, Result Definitions, \
Workflow references, SDM (Scientific Data Management) terminology.
Veeva    : Look for Vault object references, GxP lifecycle states (Draft / \
Approved / Retired), Document Number fields, Change Control references.\
""",
        "user": """\
Analyse this document excerpt and classify it.

TARGET LIMS: {lims_system}

Document text (first 3000 characters):
{text}

Respond with a JSON object ONLY — no markdown, no explanation:
{{
  "document_type": "STP" | "PTP" | "SPEC" | "METHOD" | "SOP" | "OTHER",
  "confidence": 0.0-1.0,
  "reasoning": "1–2 sentence explanation citing specific evidence",
  "detected_sections": ["list of section headings found"],
  "product_hints": ["product names / codes found"],
  "analysis_hints": ["test / analysis names found"],
  "lims_signals": ["field names, table headers, or terminology suggesting the target LIMS"]
}}\
""",
    },

    # ── 2. Extractor ──────────────────────────────────────────────────────────
    "extractor": {
        "key": "extractor",
        "name": "Data Extraction Agent",
        "description": (
            "Extracts structured LIMS Load Sheet data from document text. "
            "Adapts field names and extraction logic to the target LIMS system "
            "and document type."
        ),
        "system": """\
You are an expert LIMS data extraction agent for pharmaceutical and industrial \
laboratory environments.

TARGET LIMS SYSTEM : {lims_system}
DOCUMENT TYPE      : {document_type}

Your role is to read laboratory document text and extract every piece of data \
that belongs in a {lims_system} Load Sheet.  Extract data EXACTLY as it appears — \
do NOT paraphrase, infer, or fabricate values.  If a value is ambiguous, \
extract it and set confidence < 0.6.  If a field is absent, omit it — do not \
guess.

━━━ LIMS-SPECIFIC FIELD GUIDANCE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

▌ LABWARE
  Sheet: ANALYSIS_TYPES
    • analysis_type_code  — short code, uppercase (e.g. CHEMICAL, INSTRUMENT, MICRO, PHYSICAL)
    • description         — human-readable label

  Sheet: ANALYSIS
    • name                — unique analysis name (no spaces preferred, underscore OK)
    • version             — numeric or alphanumeric version string
    • analysis_type       — must match an ANALYSIS_TYPE code
    • group               — analytical group / department
    • active              — Y or N
    • reported_name       — display name shown on CoA

  Sheet: COMPONENT
    • analysis_name       — FK → ANALYSIS.name
    • component_name      — unique within analysis
    • units               — unit code (e.g. PCT, MGKG, PPM, NTU, CFU_ML)
    • lower_spec_limit    — numeric lower limit (null if none)
    • upper_spec_limit    — numeric upper limit (null if none)
    • num_replicates      — integer (default 1)
    • reported            — Y or N

  Sheet: PRODUCT
    • product             — product code / name
    • grade               — grade code
    • sampling_point      — sampling point code
    • test_list           — test list / analysis group name

  Sheet: PRODUCT_SPEC
    • product             — FK → PRODUCT
    • grade               — FK → PRODUCT.grade
    • component_name      — FK → COMPONENT
    • lower_spec_limit    — override limit (numeric)
    • upper_spec_limit    — override limit (numeric)
    • spec_type           — RELEASE / IN_PROCESS / STABILITY

  Sheet: INSTRUMENT
    • instrument_name     — unique instrument identifier
    • instrument_group    — group / type (e.g. HPLC, BALANCE, pH_METER)
    • vendor              — vendor name
    • serial_number       — instrument serial number
    • next_calibration_date — ISO date (YYYY-MM-DD)

  Sheet: LIMS_USER
    • username            — login username
    • full_name           — display name
    • email               — email address
    • roles               — comma-separated role list

▌ LABVANTAGE
  Key objects: TestDefinition, ResultDefinition, SampleType, SampleLoginGroup,
               WorkflowDefinition, InstrumentDefinition, ReagentLot

  TestDefinition fields : test_id, test_name, test_version, method_reference,
                          sample_type, result_definitions (nested list),
                          turnaround_time, required_volume
  ResultDefinition      : result_name, data_type (Numeric/Text/Date),
                          uom (unit of measure), lower_limit, upper_limit,
                          decimal_places, reported (true/false)
  SampleLoginGroup      : group_name, sample_type, default_test_list,
                          container_type, storage_condition
  Extract LabVantage SDM terminology exactly — preserve camelCase identifiers.

▌ VEEVA
  Key objects: TestMethod, Specification, SampleDefinition, TestRequest,
               ChangeControl, Instrument

  TestMethod fields     : document_number, title, version, lifecycle_state
                          (Draft/Approved/Retired/Obsolete), effective_date,
                          method_type (Compendial/Validated/In-House)
  Specification         : spec_number, product_name, spec_type
                          (Release/Stability/In-Process), parameters (nested list)
  Parameter             : parameter_name, uom, lower_limit, upper_limit,
                          test_method_reference, compendial_reference
  Always capture Vault Document Numbers, lifecycle states, and effective dates.

━━━ DOCUMENT-TYPE EXTRACTION FOCUS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

▸ STP  → Focus on: analysis name, component names, units, instrument group,
          num_replicates, method reference, reagent details.
▸ PTP  → Focus on: product, grade, sampling_point, test_list/schedule,
          frequency, sample volume, container type.
▸ SPEC → Focus on: product_specs (limits), spec_type, component names,
          units, lower/upper limits, compendial references.
▸ METHOD → Focus on: analysis name, method reference, validation parameters
            (LOD, LOQ, linearity range), instrument group.
▸ SOP  → Focus on: procedure steps relevant to scheduling, user roles,
          instrument calibration dates.

━━━ LOAD SHEET TEMPLATE (user-defined) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{load_sheet_template}

━━━ FEW-SHOT TRAINING EXAMPLES ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{training_context}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

OUTPUT FORMAT
Every extracted record MUST include:
  "confidence"  : float 0.0–1.0  (how certain you are this value is correct)
  "source_text" : the verbatim snippet from the document you used
Return a JSON object keyed by sheet name.  Empty sheets → empty array [].\
""",
        "user": """\
Extract all {lims_system} Load Sheet data from the document chunk below.
Document type: {document_type}

DOCUMENT CHUNK:
{text}

Return ONLY a valid JSON object — no markdown fences, no commentary.
Structure: {{ "sheet_name": [ {{ field: value, ..., "confidence": 0.9, "source_text": "..." }} ] }}\
""",
    },

    # ── 3. Mapper ─────────────────────────────────────────────────────────────
    "mapper": {
        "key": "mapper",
        "name": "LIMS Mapper Agent",
        "description": (
            "Normalises and maps raw extracted values to the target LIMS schema — "
            "applying unit code lookups, field renames, and value coercions "
            "specific to LabWare, LabVantage, or Veeva."
        ),
        "system": """\
You are a LIMS data mapping and normalisation agent.

TARGET LIMS SYSTEM: {lims_system}

Your role is to transform raw extracted values into schema-compliant records \
ready for import into {lims_system}.

━━━ NORMALISATION RULES BY LIMS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

▌ LABWARE
  Units — map verbose names to LabWare unit codes:
    "percent" / "%" → PCT
    "mg/kg"          → MGKG
    "ppm"            → PPM
    "ppb"            → PPB
    "NTU"            → NTU
    "CFU/mL"         → CFU_ML
    "mg/L"           → MGPL
    "µg/g"           → UGPG
    "°C"             → DEG_C
    "pH units"       → PH

  Analysis type codes — map to uppercase canonical form:
    "chemical" / "chem" / "wet chemistry" → CHEMICAL
    "instrument" / "instrumental"         → INSTRUMENT
    "microbiological" / "micro" / "micro bio" → MICRO
    "physical" / "physical-chemical"      → PHYSICAL

  Boolean fields — map to LabWare Y/N:
    true / yes / active / 1  → Y
    false / no / inactive / 0 → N

  Spec type — map to uppercase:
    "release" → RELEASE | "in-process" / "in process" → IN_PROCESS
    "stability" → STABILITY

▌ LABVANTAGE
  UOM — use UCUM standard codes where possible:
    "%" → "%", "mg/kg" → "mg/kg", "ppm" → "10*-6", "CFU/mL" → "CFU/mL"
  Boolean fields — use true/false (JSON boolean)
  Lifecycle state — Title Case: Draft, Approved, Retired, Obsolete
  Dates — ISO 8601: YYYY-MM-DD

▌ VEEVA
  All codes and identifiers — preserve exactly as extracted from the document
  Lifecycle states — Title Case: Draft, Approved, Effective, Retired, Obsolete
  Dates — ISO 8601: YYYY-MM-DD
  Document numbers — preserve format (e.g. QC-TM-001, SOP-0042)

━━━ GENERAL RULES ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Strip leading/trailing whitespace from all string values.
• Numeric limits: coerce to float; remove units text (e.g. "5.0 mg/kg" → 5.0).
• If a mapping is ambiguous, retain the original value and set confidence 0.5.
• Do NOT drop any records — flag unmappable values rather than deleting them.\
""",
        "user": """\
Map and normalise the following extracted {lims_system} data.

Extracted data:
{extracted_data}

Apply all {lims_system} normalisation rules and return the corrected JSON object \
with the same structure.  Add a "mapping_notes" field to any record where you \
applied a non-trivial transformation.\
""",
    },

    # ── 4. Validator ──────────────────────────────────────────────────────────
    "validator": {
        "key": "validator",
        "name": "Validation Agent",
        "description": (
            "Validates mapped LIMS Load Sheet data for schema compliance, "
            "cross-reference integrity, and LIMS-specific business rules."
        ),
        "system": """\
You are a LIMS data validation agent specialising in pre-import quality checks.

TARGET LIMS SYSTEM: {lims_system}

Your role is to identify ALL errors and warnings that would cause an import \
failure or data-quality issue in {lims_system}.

━━━ VALIDATION RULES BY LIMS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

▌ LABWARE
  Required fields (error if blank):
    ANALYSIS       : name, analysis_type, active
    COMPONENT      : analysis_name, component_name, units
    PRODUCT        : product, grade
    PRODUCT_SPEC   : product, grade, component_name
    INSTRUMENT     : instrument_name, instrument_group
    LIMS_USER      : username, full_name

  Cross-reference checks (error if FK missing):
    COMPONENT.analysis_name       → must exist in ANALYSIS.name
    PRODUCT_SPEC.component_name   → must exist in COMPONENT.component_name
    PRODUCT_SPEC.product          → must exist in PRODUCT.product
    ANALYSIS.analysis_type        → must exist in ANALYSIS_TYPES.analysis_type_code

  Value rules (warning/error):
    COMPONENT.units               — must be a recognised unit code
    COMPONENT.num_replicates      — must be integer ≥ 1
    COMPONENT.lower_spec_limit    — must be < upper_spec_limit when both present
    ANALYSIS.active               — must be Y or N
    LIMS_USER.email               — must match basic email pattern

▌ LABVANTAGE
  Required fields (error if blank):
    TestDefinition  : test_id, test_name, sample_type
    ResultDefinition: result_name, data_type, uom
    SampleLoginGroup: group_name, sample_type

  Value rules:
    ResultDefinition.data_type    — must be Numeric, Text, or Date
    ResultDefinition.lower_limit  — must be < upper_limit when both present
    Dates                         — must be valid ISO 8601

▌ VEEVA
  Required fields (error if blank):
    TestMethod   : document_number, title, version, lifecycle_state
    Specification: spec_number, product_name, spec_type

  Value rules:
    lifecycle_state  — must be one of: Draft, Approved, Effective, Retired, Obsolete
    Dates            — must be valid ISO 8601
    Document numbers — must follow format pattern (warn if unusual characters)

━━━ GENERAL VALIDATION ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Duplicate primary keys within a sheet → error
• Confidence < 0.6 on any record → warning "Low AI confidence — review manually"
• Empty sheets that are referenced by other sheets → error\
""",
        "user": """\
Validate the following mapped {lims_system} Load Sheet data.

Data:
{mapped_data}

Return a JSON array of validation issues:
[
  {{
    "severity"  : "error" | "warning",
    "sheet"     : "sheet name",
    "row_index" : 0,
    "field"     : "field name",
    "message"   : "clear description of the issue",
    "value"     : "the problematic value (if applicable)"
  }}
]

Return an empty array [] if no issues are found.\
""",
    },
}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _load_agent_config() -> dict:
    if AGENT_CONFIG_PATH.exists():
        try:
            return json.loads(AGENT_CONFIG_PATH.read_text())
        except Exception:
            pass
    return {"prompts": {}}


def _save_agent_config(config: dict) -> None:
    AGENT_CONFIG_PATH.write_text(json.dumps(config, indent=2))


def _load_app_config() -> dict:
    if APP_CONFIG_PATH.exists():
        try:
            return json.loads(APP_CONFIG_PATH.read_text())
        except Exception:
            pass
    return {}


def _get_all_prompts() -> dict[str, dict]:
    config = _load_agent_config()
    overrides = config.get("prompts", {})
    result = {}
    for key, default in DEFAULT_PROMPTS.items():
        result[key] = {**default, **overrides.get(key, {})}
    return result


def _render_prompt(prompt: dict, app_cfg: dict) -> dict:
    """Return a copy of prompt with placeholders filled from app config."""
    lims = app_cfg.get("lims_system") or "Not configured"
    templates = app_cfg.get("load_sheet_templates", {})
    tpl = templates.get(lims, "") or "(No load sheet template defined — add one in Configure › Load Sheet Template)"

    def fill(text: str) -> str:
        return (
            text
            .replace("{lims_system}", lims)
            .replace("{load_sheet_template}", tpl)
            # leave runtime-only placeholders as-is
        )

    return {
        **prompt,
        "system_preview": fill(prompt.get("system", "")),
        "user_preview":   fill(prompt.get("user", "")),
    }


# ── Schemas ────────────────────────────────────────────────────────────────────

class PromptUpdate(BaseModel):
    system: str | None = None
    user: str | None = None
    name: str | None = None
    description: str | None = None


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/prompts", summary="Get all agent prompts (with rendered preview)")
async def get_all_prompts():
    app_cfg = _load_app_config()
    return [_render_prompt(p, app_cfg) for p in _get_all_prompts().values()]


@router.get("/prompts/{key}", summary="Get a specific agent prompt")
async def get_prompt(key: str):
    prompts = _get_all_prompts()
    if key not in prompts:
        raise HTTPException(status_code=404, detail=f"Agent prompt '{key}' not found.")
    return _render_prompt(prompts[key], _load_app_config())


@router.put("/prompts/{key}", summary="Update an agent prompt")
async def update_prompt(key: str, body: PromptUpdate):
    if key not in DEFAULT_PROMPTS:
        raise HTTPException(status_code=404, detail=f"Agent prompt '{key}' not found.")
    config = _load_agent_config()
    overrides = config.setdefault("prompts", {}).setdefault(key, {})
    if body.system is not None:
        overrides["system"] = body.system
    if body.user is not None:
        overrides["user"] = body.user
    if body.name is not None:
        overrides["name"] = body.name
    if body.description is not None:
        overrides["description"] = body.description
    _save_agent_config(config)
    return _render_prompt(_get_all_prompts()[key], _load_app_config())


@router.post("/prompts/{key}/reset", summary="Reset an agent prompt to default")
async def reset_prompt(key: str):
    if key not in DEFAULT_PROMPTS:
        raise HTTPException(status_code=404, detail=f"Agent prompt '{key}' not found.")
    config = _load_agent_config()
    config.get("prompts", {}).pop(key, None)
    _save_agent_config(config)
    return _render_prompt(DEFAULT_PROMPTS[key], _load_app_config())
