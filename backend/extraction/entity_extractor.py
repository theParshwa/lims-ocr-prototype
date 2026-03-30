"""
entity_extractor.py - Extract all LIMS entities in a single LLM call per chunk.

Extracts data for all 30 LIMS Load Sheet tabs from pharmaceutical specification
documents. Uses one combined prompt per chunk to minimise API calls.
"""

from __future__ import annotations

import json
import logging
import re
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


def _clean_json(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
    return raw.strip()


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
    """

    def __init__(self, chunk_size: int = 12000, chunk_overlap: int = 200) -> None:
        self._llm = get_llm()
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
    ) -> dict[str, list]:
        combined = text
        if tables_text:
            combined += "\n\n--- TABLES ---\n" + tables_text

        self._training_context = training_context

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
        """Run one combined LLM call and parse all entity types."""
        try:
            messages = [
                SystemMessage(content=COMBINED_SYSTEM),
                HumanMessage(content=COMBINED_USER.format(text=chunk)),
            ]
            response = self._llm.invoke(messages)
            raw = _clean_json(response.content)
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.warning("JSON parse error on chunk: %s", exc)
            return {}
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
