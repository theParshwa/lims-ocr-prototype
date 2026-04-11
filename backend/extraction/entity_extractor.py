"""
entity_extractor.py - Extract all LIMS entities in a single LLM call per chunk.

Extracts data for all 30 LIMS Load Sheet tabs from pharmaceutical specification
documents. Uses one combined prompt per chunk to minimise API calls.

Uses OpenAI structured outputs (response_format: json_schema, strict=True) to
guarantee valid JSON with no hallucinated field names.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import ValidationError

from models.schemas import (
    AnalysisTypeRecord,
    CommonNameRecord,
    AnalysisRecord,
    ComponentRecord,
    UnitRecord,
    ProductRecord,
    TPHGradeRecord,
    SamplingPointRecord,
    ProductGradeRecord,
    ProdGradeStageRecord,
    ProductSpecRecord,
    TPHItemCodeRecord,
    TPHItemCodeSpecRecord,
    TPHItemCodeSuppRecord,
    TPHSamplePlanRecord,
    TPHSamplePlanEntryRecord,
    CustomerRecord,
    TSiteRecord,
    TPlantRecord,
    TSuiteRecord,
    ProcessUnitRecord,
    ProcSchedParentRecord,
    ProcessScheduleRecord,
    ListRecord,
    ListEntryRecord,
    VendorRecord,
    SupplierRecord,
    InstrumentRecord,
    LimsUserRecord,
    VersionRecord,
    SHEET_KEYS,
)
from .llm_factory import get_llm

logger = logging.getLogger(__name__)


# ── JSON Schema helpers ───────────────────────────────────────────────────────

def _s(t: str) -> dict:
    """Required scalar property."""
    return {"type": t}


def _o(t: str) -> dict:
    """Optional (nullable) scalar property."""
    return {"anyOf": [{"type": t}, {"type": "null"}]}


def _obj(props: dict) -> dict:
    """Strict-mode object schema: all props required, no extras."""
    return {
        "type": "object",
        "properties": props,
        "required": list(props.keys()),
        "additionalProperties": False,
    }


def _arr(item_schema: dict) -> dict:
    return {"type": "array", "items": item_schema}


# ── Per-sheet item schemas (only LLM output fields; no internal annotations) ─

_CONFIDENCE = {"confidence": _s("number")}

_ANALYSIS_TYPE_ITEM = _obj({
    "name": _s("string"), "description": _o("string"), "group_name": _o("string"),
    **_CONFIDENCE,
})
_COMMON_NAME_ITEM = _obj({
    "name": _s("string"), "description": _o("string"), "group_name": _o("string"),
    **_CONFIDENCE,
})
_ANALYSIS_ITEM = _obj({
    "name": _s("string"), "version": _o("string"), "group_name": _o("string"),
    "active": _o("string"), "reported_name": _o("string"), "common_name": _o("string"),
    "analysis_type": _o("string"), "description": _o("string"),
    **_CONFIDENCE,
})
_COMPONENT_ITEM = _obj({
    "analysis": _s("string"), "name": _s("string"),
    "num_replicates": _o("integer"), "version": _o("string"), "order_number": _o("integer"),
    "result_type": _o("string"), "units": _o("string"),
    "minimum": _o("number"), "maximum": _o("number"),
    **_CONFIDENCE,
})
_UNIT_ITEM = _obj({
    "unit_code": _s("string"), "description": _o("string"),
    "display_string": _o("string"), "group_name": _o("string"),
    **_CONFIDENCE,
})
_PRODUCT_ITEM = _obj({
    "product": _s("string"), "version": _o("string"), "sampling_point": _o("string"),
    "grade": _o("string"), "order_number": _o("integer"), "description": _o("string"),
    "continue_checking": _o("string"), "test_list": _o("string"), "always_check": _o("string"),
    **_CONFIDENCE,
})
_TPH_GRADE_ITEM = _obj({
    "name": _s("string"), "description": _o("string"), "group_name": _o("string"),
    "active": _o("string"), "code": _o("string"),
    **_CONFIDENCE,
})
_SAMPLING_POINT_ITEM = _obj({
    "name": _s("string"), "description": _o("string"), "group_name": _o("string"),
    **_CONFIDENCE,
})
_PRODUCT_GRADE_ITEM = _obj({
    "product": _o("string"), "version": _o("string"), "grade": _o("string"),
    "order_number": _o("integer"), "description": _o("string"),
    "continue_checking": _o("string"), "test_list": _o("string"), "always_check": _o("string"),
    **_CONFIDENCE,
})
_PROD_GRADE_STAGE_ITEM = _obj({
    "product": _s("string"), "version": _o("string"), "sampling_point": _o("string"),
    "grade": _o("string"), "stage": _o("string"), "analysis": _o("string"),
    "order_number": _o("integer"), "description": _o("string"), "spec_type": _o("string"),
    "num_reps": _o("integer"), "partial": _o("string"), "ext_link": _o("string"),
    "reported_name": _o("string"), "variation": _o("string"), "required": _o("string"),
    **_CONFIDENCE,
})
_PRODUCT_SPEC_ITEM = _obj({
    "product": _s("string"), "version": _o("string"), "sampling_point": _o("string"),
    "grade": _o("string"), "stage": _o("string"), "analysis": _o("string"),
    "component": _o("string"), "units": _o("string"), "round": _o("integer"),
    "rule_type": _o("string"), "spec_rule": _o("string"),
    "min_value": _o("number"), "max_value": _o("number"), "text_value": _o("string"),
    "class": _o("string"), "required": _o("string"),
    **_CONFIDENCE,
})
_TPH_ITEM_CODE_ITEM = _obj({
    "t_ph_item_code": _s("string"), "supplier": _o("string"), "active": _o("string"),
    "status1": _o("string"), "status2": _o("string"), "order_number": _o("integer"),
    "retest_interval": _o("integer"), "expiry_interval": _o("integer"),
    "full_test_freq": _o("integer"), "lots_to_go": _o("integer"), "date_last_tested": _o("string"),
    **_CONFIDENCE,
})
_TPH_ITEM_CODE_SPEC_ITEM = _obj({
    "spec_code": _o("string"), "t_ph_item_code": _s("string"), "product_spec": _o("string"),
    "spec_class": _o("string"), "order_number": _o("integer"),
    "grade": _o("string"), "common_grade": _o("string"),
    **_CONFIDENCE,
})
_TPH_ITEM_CODE_SUPP_ITEM = _obj({
    "t_ph_item_code": _s("string"), "supplier": _o("string"), "active": _o("string"),
    "status1": _o("string"), "status2": _o("string"), "order_number": _o("integer"),
    **_CONFIDENCE,
})
_TPH_SAMPLE_PLAN_ITEM = _obj({
    "name": _s("string"), "version": _o("string"), "active": _o("string"),
    "description": _o("string"), "group_name": _o("string"),
    **_CONFIDENCE,
})
_TPH_SAMPLE_PLAN_ENTRY_ITEM = _obj({
    "t_ph_sample_plan": _s("string"), "entry_code": _o("string"), "version": _o("string"),
    "description": _o("string"), "order_number": _o("integer"), "spec_type": _o("string"),
    "spec_status": _o("string"), "t_ph_sample_type": _o("string"),
    "log_sample": _o("string"), "create_inventory": _o("string"),
    "retained_sample": _o("string"), "stability": _o("string"),
    "initial_status": _o("string"), "indic_samples": _o("integer"),
    "quantity": _o("number"), "units": _o("string"),
    **_CONFIDENCE,
})
_CUSTOMER_ITEM = _obj({
    "name": _s("string"), "group_name": _o("string"), "description": _o("string"),
    "company_name": _o("string"), "address1": _o("string"), "address2": _o("string"),
    "address3": _o("string"), "address4": _o("string"), "address5": _o("string"),
    "address6": _o("string"), "fax_num": _o("string"), "phone_num": _o("string"),
    "contact": _o("string"), "email_addr": _o("string"),
    **_CONFIDENCE,
})
_T_SITE_ITEM = _obj({
    "name": _s("string"), "description": _o("string"), "group_name": _o("string"),
    "parent_site": _o("string"),
    **_CONFIDENCE,
})
_T_PLANT_ITEM = _obj({
    "name": _s("string"), "description": _o("string"), "group_name": _o("string"),
    "site": _o("string"), "personnel_smp_type": _o("string"),
    "personnel_stage": _o("string"), "personnel_spec_type": _o("string"),
    **_CONFIDENCE,
})
_T_SUITE_ITEM = _obj({
    "name": _s("string"), "description": _o("string"), "group_name": _o("string"),
    "plant": _o("string"), "visual_workflow": _o("string"),
    "corrective_action": _o("string"), "restrict_collection": _o("string"),
    **_CONFIDENCE,
})
_PROCESS_UNIT_ITEM = _obj({
    "name": _s("string"), "description": _o("string"), "group_name": _o("string"),
    "product_grade": _o("string"), "sample_template": _o("string"),
    "running": _o("string"), "phase": _o("string"), "default_phase": _o("string"),
    "t_alternate_grade": _o("string"), "t_corrective_action": _o("string"), "t_suite": _o("string"),
    **_CONFIDENCE,
})
_PROC_SCHED_PARENT_ITEM = _obj({
    "name": _s("string"), "first_day_of_week": _o("string"),
    "treat_holidays_as": _o("string"), "workstation": _o("string"),
    "running": _o("string"), "description": _o("string"), "group_name": _o("string"),
    "active_flag": _o("string"), "version": _o("string"), "t_site": _o("string"),
    **_CONFIDENCE,
})
_PROCESS_SCHEDULE_ITEM = _obj({
    "schedule_number": _o("string"), "schedule_name": _o("string"),
    "unit": _o("string"), "sampling_point": _o("string"), "description": _o("string"),
    "order_number": _o("integer"), "running": _o("string"), "phase": _o("string"),
    "version": _o("string"), "spec_type": _o("string"), "stage": _o("string"),
    **_CONFIDENCE,
})
_LIST_ITEM = _obj({
    "list": _s("string"), "name": _s("string"),
    "value": _o("string"), "order_number": _o("integer"),
    **_CONFIDENCE,
})
_LIST_ENTRY_ITEM = _obj({
    "name": _s("string"), "group_name": _o("string"), "description": _o("string"),
    **_CONFIDENCE,
})
_VENDOR_ITEM = _obj({
    "name": _s("string"), "description": _o("string"), "contact": _o("string"),
    "company_name": _o("string"), "address1": _o("string"), "address2": _o("string"),
    "address3": _o("string"), "address4": _o("string"), "address5": _o("string"),
    "address6": _o("string"), "fax_num": _o("string"), "phone_num": _o("string"),
    "group_name": _o("string"),
    **_CONFIDENCE,
})
_SUPPLIER_ITEM = _obj({
    "name": _s("string"), "description": _o("string"), "contact": _o("string"),
    "company_name": _o("string"), "address1": _o("string"), "address2": _o("string"),
    "address3": _o("string"), "address4": _o("string"), "address5": _o("string"),
    "address6": _o("string"), "fax_num": _o("string"), "phone_num": _o("string"),
    "group_name": _o("string"),
    **_CONFIDENCE,
})
_INSTRUMENT_ITEM = _obj({
    "name": _s("string"), "group_name": _o("string"), "description": _o("string"),
    "inst_group": _o("string"), "vendor": _o("string"), "on_line": _o("string"),
    "serial_no": _o("string"), "pm_date": _o("string"), "pm_intv": _o("string"),
    "calib_date": _o("string"), "calib_intv": _o("string"), "model_no": _o("string"),
    **_CONFIDENCE,
})
_LIMS_USER_ITEM = _obj({
    "user_name": _s("string"), "full_name": _o("string"), "phone": _o("string"),
    "group_name": _o("string"), "description": _o("string"), "email_addr": _o("string"),
    "is_role": _o("string"), "uses_roles": _o("string"), "language_prefix": _o("string"),
    "t_site": _o("string"), "location_lab": _o("string"),
    **_CONFIDENCE,
})
_VERSION_ITEM = _obj({
    "table_name": _o("string"), "version": _o("string"), "description": _o("string"),
    **_CONFIDENCE,
})

# Combined top-level schema passed to OpenAI structured outputs
_EXTRACTION_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "analysis_types", "common_names", "analysis", "components", "units",
        "products", "tph_grades", "sampling_points", "product_grades",
        "prod_grade_stages", "product_specs", "tph_item_codes",
        "tph_item_code_specs", "tph_item_code_supps", "tph_sample_plans",
        "tph_sample_plan_entries", "customers", "t_sites", "t_plants",
        "t_suites", "process_units", "proc_sched_parents", "process_schedules",
        "lists", "list_entries", "vendors", "suppliers", "instruments",
        "lims_users", "versions",
    ],
    "properties": {
        "analysis_types":         _arr(_ANALYSIS_TYPE_ITEM),
        "common_names":           _arr(_COMMON_NAME_ITEM),
        "analysis":               _arr(_ANALYSIS_ITEM),
        "components":             _arr(_COMPONENT_ITEM),
        "units":                  _arr(_UNIT_ITEM),
        "products":               _arr(_PRODUCT_ITEM),
        "tph_grades":             _arr(_TPH_GRADE_ITEM),
        "sampling_points":        _arr(_SAMPLING_POINT_ITEM),
        "product_grades":         _arr(_PRODUCT_GRADE_ITEM),
        "prod_grade_stages":      _arr(_PROD_GRADE_STAGE_ITEM),
        "product_specs":          _arr(_PRODUCT_SPEC_ITEM),
        "tph_item_codes":         _arr(_TPH_ITEM_CODE_ITEM),
        "tph_item_code_specs":    _arr(_TPH_ITEM_CODE_SPEC_ITEM),
        "tph_item_code_supps":    _arr(_TPH_ITEM_CODE_SUPP_ITEM),
        "tph_sample_plans":       _arr(_TPH_SAMPLE_PLAN_ITEM),
        "tph_sample_plan_entries": _arr(_TPH_SAMPLE_PLAN_ENTRY_ITEM),
        "customers":              _arr(_CUSTOMER_ITEM),
        "t_sites":                _arr(_T_SITE_ITEM),
        "t_plants":               _arr(_T_PLANT_ITEM),
        "t_suites":               _arr(_T_SUITE_ITEM),
        "process_units":          _arr(_PROCESS_UNIT_ITEM),
        "proc_sched_parents":     _arr(_PROC_SCHED_PARENT_ITEM),
        "process_schedules":      _arr(_PROCESS_SCHEDULE_ITEM),
        "lists":                  _arr(_LIST_ITEM),
        "list_entries":           _arr(_LIST_ENTRY_ITEM),
        "vendors":                _arr(_VENDOR_ITEM),
        "suppliers":              _arr(_SUPPLIER_ITEM),
        "instruments":            _arr(_INSTRUMENT_ITEM),
        "lims_users":             _arr(_LIMS_USER_ITEM),
        "versions":               _arr(_VERSION_ITEM),
    },
}


COMBINED_SYSTEM = """You are an expert LIMS (Laboratory Information Management System) data extraction specialist.
You extract data from pharmaceutical specification documents (drug specs, STPs, methods) and map them
into a standard LIMS Load Sheet format with 30 sheets.

Your job is to read the document text and populate as many of the 30 sheet types as possible.
The primary sheets you'll extract from spec documents are:

1. ANALYSIS_TYPES - Categories of analyses (CHEMICAL, INSTRUMENT, MICRO, etc.)
2. COMMON_NAME - Common abbreviations for tests (e.g. LOD = Loss on drying)
3. ANALYSIS - Each test/analysis method mentioned (with NAME as UPPERCASE_CODE)
4. COMPONENT - Specific parameters measured within each analysis
5. UNITS - All measurement units referenced (%, mg/kg, °C, CFU/g, etc.)
6. PRODUCT - The product(s) being specified
7. T_PH_GRADE - Quality grades referenced
8. SAMPLING_POINT - Where/when samples are taken (Receiving, In-Process, Final)
9. PRODUCT_GRADE - Product-grade combinations
10. PROD_GRADE_STAGE - Which analyses apply at each product/grade/stage
11. PRODUCT_SPEC - Acceptance limits (min/max/pass-fail) for each test
12. T_PH_ITEM_CODE - Pharmaceutical item codes
13. T_PH_ITEM_CODE_SPEC - Item code to specification mappings
14. T_PH_ITEM_CODE_SUPP - Item code supplier associations
15. T_PH_SAMPLE_PLAN - Sampling plan definitions
16. T_PH_SAMPLE_PLAN_EN - Sampling plan entries/details

Sheets 17-30 (CUSTOMER, T_SITE, T_PLANT, T_SUITE, PROCESS_UNIT, PROC_SCHED_PARENT,
PROCESS_SCHEDULE, LIST, LIST_ENTRY, VENDOR, SUPPLIER, INSTRUMENTS, LIMS_USERS, VERSIONS)
are typically organizational/configuration data. Only populate these if the document
explicitly mentions them.

Key extraction rules:
- Analysis NAME must be UPPERCASE_WITH_UNDERSCORES (e.g. LOSS_ON_DRYING, ASSAY, PH)
- Each parameter/test in the spec creates both an ANALYSIS and a COMPONENT record
- Acceptance criteria (min/max/limits) go into PRODUCT_SPEC
- The PRODUCT_SPEC.analysis and PRODUCT_SPEC.component must match ANALYSIS.name and COMPONENT.name
- Units should use standard codes: PCT (%), PPM (ppm), CELSIUS (°C), etc.
- Set confidence < 0.7 for uncertain mappings"""

COMBINED_USER = """Extract all LIMS entities from this pharmaceutical document text.
Return ONLY a single JSON object with the keys listed below.
Use empty arrays [] for entity types not found in this text.

Text:
{text}

Return this exact JSON structure (no markdown, no extra text):
{{
  "analysis_types": [
    {{"name": "CHEMICAL", "description": "Chemical analysis", "group_name": null, "confidence": 0.9}}
  ],
  "common_names": [
    {{"name": "LOD", "description": "Loss on drying", "group_name": null, "confidence": 0.9}}
  ],
  "analysis": [
    {{"name": "UPPERCASE_CODE", "version": null, "group_name": "Physical|Chemical|Microbiological", "active": "T", "reported_name": "Human readable name", "common_name": null, "analysis_type": "CHEMICAL|INSTRUMENT|MICRO", "description": "description", "confidence": 0.9}}
  ],
  "components": [
    {{"analysis": "PARENT_ANALYSIS_CODE", "name": "component name", "num_replicates": 1, "version": null, "order_number": 1, "result_type": "Numeric|Text|Pass/Fail", "units": "unit_code", "minimum": null, "maximum": null, "confidence": 0.9}}
  ],
  "units": [
    {{"unit_code": "PCT", "description": "Percentage", "display_string": "%", "group_name": null, "confidence": 0.95}}
  ],
  "products": [
    {{"product": "PRODUCT_NAME", "version": null, "sampling_point": null, "grade": null, "order_number": null, "description": "description", "continue_checking": null, "test_list": null, "always_check": null, "confidence": 0.9}}
  ],
  "tph_grades": [
    {{"name": "GRADE_NAME", "description": null, "group_name": null, "active": "T", "code": null, "confidence": 0.8}}
  ],
  "sampling_points": [
    {{"name": "SAMPLING_POINT", "description": null, "group_name": null, "confidence": 0.85}}
  ],
  "product_grades": [
    {{"product": "PRODUCT_NAME", "version": null, "grade": null, "order_number": null, "description": null, "continue_checking": null, "test_list": null, "always_check": null, "confidence": 0.8}}
  ],
  "prod_grade_stages": [
    {{"product": "PRODUCT_NAME", "version": null, "sampling_point": null, "grade": null, "stage": null, "analysis": "ANALYSIS_CODE", "order_number": 1, "description": null, "spec_type": "Release", "num_reps": 1, "partial": null, "ext_link": null, "reported_name": null, "variation": null, "required": "Y", "confidence": 0.8}}
  ],
  "product_specs": [
    {{"product": "PRODUCT_NAME", "version": null, "sampling_point": null, "grade": null, "stage": null, "analysis": "ANALYSIS_CODE", "component": "COMPONENT_NAME", "units": "unit_code", "round": null, "rule_type": "Limit|Pass/Fail", "spec_rule": "Between|LessThan|GreaterThan|Text", "min_value": null, "max_value": null, "text_value": null, "class": null, "required": "Y", "confidence": 0.85}}
  ],
  "tph_item_codes": [],
  "tph_item_code_specs": [],
  "tph_item_code_supps": [],
  "tph_sample_plans": [],
  "tph_sample_plan_entries": [],
  "customers": [],
  "t_sites": [],
  "t_plants": [],
  "t_suites": [],
  "process_units": [],
  "proc_sched_parents": [],
  "process_schedules": [],
  "lists": [],
  "list_entries": [],
  "vendors": [],
  "suppliers": [],
  "instruments": [],
  "lims_users": [],
  "versions": []
}}"""


# Mapping from JSON key → Pydantic model class
_MODEL_MAP: dict[str, type] = {
    "analysis_types": AnalysisTypeRecord,
    "common_names": CommonNameRecord,
    "analysis": AnalysisRecord,
    "components": ComponentRecord,
    "units": UnitRecord,
    "products": ProductRecord,
    "tph_grades": TPHGradeRecord,
    "sampling_points": SamplingPointRecord,
    "product_grades": ProductGradeRecord,
    "prod_grade_stages": ProdGradeStageRecord,
    "product_specs": ProductSpecRecord,
    "tph_item_codes": TPHItemCodeRecord,
    "tph_item_code_specs": TPHItemCodeSpecRecord,
    "tph_item_code_supps": TPHItemCodeSuppRecord,
    "tph_sample_plans": TPHSamplePlanRecord,
    "tph_sample_plan_entries": TPHSamplePlanEntryRecord,
    "customers": CustomerRecord,
    "t_sites": TSiteRecord,
    "t_plants": TPlantRecord,
    "t_suites": TSuiteRecord,
    "process_units": ProcessUnitRecord,
    "proc_sched_parents": ProcSchedParentRecord,
    "process_schedules": ProcessScheduleRecord,
    "lists": ListRecord,
    "list_entries": ListEntryRecord,
    "vendors": VendorRecord,
    "suppliers": SupplierRecord,
    "instruments": InstrumentRecord,
    "lims_users": LimsUserRecord,
    "versions": VersionRecord,
}


def _parse_records(items: list[dict], model_class: type) -> list:
    records = []
    for item in items:
        try:
            records.append(model_class(**item))
        except (ValidationError, TypeError) as exc:
            logger.debug("Skipping invalid %s: %s", model_class.__name__, exc)
    return records


class EntityExtractor:
    """
    Extract all LIMS entities using ONE LLM call per chunk.
    Supports all 30 LIMS Load Sheet tabs.

    Uses OpenAI structured outputs (strict=True) so JSON is always valid
    and field names can never be hallucinated.
    """

    def __init__(self, chunk_size: int = 12000, chunk_overlap: int = 200) -> None:
        self._llm = get_llm()
        # Bind the extraction JSON schema for structured outputs.
        # strict=True means OpenAI guarantees the response matches the schema exactly.
        self._structured_llm = self._llm.bind(
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "lims_extraction",
                    "strict": True,
                    "schema": _EXTRACTION_SCHEMA,
                },
            }
        )
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", " "],
        )
        self._training_context: str = ""

    def extract_all(
        self,
        text: str,
        tables_text: str = "",
        training_context: str = "",
        user_context: str = "",
    ) -> dict[str, list]:
        combined = text
        if tables_text:
            combined += "\n\n--- TABLES ---\n" + tables_text

        self._training_context = training_context
        self._user_context = user_context.strip() if user_context else ""

        chunks = self._splitter.split_text(combined)
        logger.info("Extracting from %d chunks (1 API call each)", len(chunks))

        results: dict[str, list] = {key: [] for key in SHEET_KEYS}

        for i, chunk in enumerate(chunks):
            logger.info("Processing chunk %d/%d...", i + 1, len(chunks))
            effective_chunk = (
                (self._training_context + "\n\n" + chunk)
                if (i == 0 and self._training_context)
                else chunk
            )
            chunk_results = self._extract_chunk(effective_chunk)
            for key in results:
                results[key].extend(chunk_results.get(key, []))

        # Deduplicate entity types that have unique keys
        results["analysis_types"]   = self._dedup(results["analysis_types"],   lambda r: r.name)
        results["common_names"]     = self._dedup(results["common_names"],     lambda r: r.name)
        results["analysis"]         = self._dedup(results["analysis"],         lambda r: r.name)
        results["components"]       = self._dedup(results["components"],       lambda r: f"{r.analysis}::{r.name}")
        results["units"]            = self._dedup(results["units"],            lambda r: r.unit_code)
        results["products"]         = self._dedup(results["products"],         lambda r: r.product)
        results["tph_grades"]       = self._dedup(results["tph_grades"],       lambda r: r.name)
        results["sampling_points"]  = self._dedup(results["sampling_points"],  lambda r: r.name)
        results["tph_item_codes"]   = self._dedup(results["tph_item_codes"],   lambda r: r.t_ph_item_code)
        results["tph_sample_plans"] = self._dedup(results["tph_sample_plans"], lambda r: r.name)

        logger.info("Extraction complete: %s", {k: len(v) for k, v in results.items()})
        return results

    def _extract_chunk(self, chunk: str) -> dict[str, list]:
        """Run one structured LLM call and parse all entity types.

        Structured outputs (strict=True) guarantee the response is valid JSON
        matching _EXTRACTION_SCHEMA, so no JSON parsing errors are possible.
        """
        try:
            system_content = COMBINED_SYSTEM
            if getattr(self, "_user_context", ""):
                system_content = (
                    system_content
                    + "\n\nADDITIONAL CONTEXT PROVIDED BY THE SUBMITTER:\n"
                    + self._user_context
                    + "\n\nTake this context into account when extracting and mapping data."
                )
            messages = [
                SystemMessage(content=system_content),
                HumanMessage(content=COMBINED_USER.format(text=chunk)),
            ]
            response = self._structured_llm.invoke(messages)
            # response.content is guaranteed valid JSON matching the schema
            data = json.loads(response.content)
        except Exception as exc:  # noqa: BLE001
            logger.error("LLM call failed: %s", exc)
            return {}

        result = {}
        for key, model_class in _MODEL_MAP.items():
            result[key] = _parse_records(data.get(key, []), model_class)
        return result

    @staticmethod
    def _dedup(records: list, key_fn: Any) -> list:
        seen: dict = {}
        for r in records:
            k = key_fn(r)
            if k not in seen or r.confidence > seen[k].confidence:
                seen[k] = r
        return list(seen.values())
