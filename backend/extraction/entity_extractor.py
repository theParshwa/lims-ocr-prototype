"""
entity_extractor.py - Extract all LIMS entities in a single LLM call per chunk.

Optimised strategy: one combined prompt per chunk extracts ALL entity types
simultaneously, reducing API calls from ~8x to 1x per chunk.
A 20-page document = ~5 chunks = ~5 API calls total.
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
    AnalysisRecord,
    ComponentRecord,
    ProdGradeStageRecord,
    ProductGradeRecord,
    ProductRecord,
    ProductSpecRecord,
    TPHItemCodeRecord,
    TPHItemCodeSpecRecord,
    TPHItemCodeSuppRecord,
    TPHSamplePlanEntryRecord,
    TPHSamplePlanRecord,
    UnitRecord,
)
from .llm_factory import get_llm

logger = logging.getLogger(__name__)


COMBINED_SYSTEM = """You are an expert LIMS (Laboratory Information Management System) data extraction specialist.
Extract ALL relevant LIMS entities from the document text provided and return them as a single JSON object.

LIMS Definitions:
- Analysis: A test method (e.g. Moisture Content, pH, TPC). Name must be UPPERCASE_WITH_UNDERSCORES.
- Component: A specific measured parameter within an Analysis.
- Units: Measurement units referenced in the document.
- Product: Products or materials being tested.
- Product Spec: Acceptance limits (min/max/pass-fail) for a product+analysis combination.
- Prod Grade Stage: Which analyses are required per product/grade/stage.
- Sample Plan: Sampling procedures and schedules.
- T PH Item Code: Pharmaceutical item/product codes."""

COMBINED_USER = """Extract all LIMS entities from this text. Return ONLY a single JSON object with these keys.
Use empty arrays [] for entity types not present in this text.

Text:
{text}

Return this exact JSON structure (no markdown, no extra text):
{{
  "analysis": [
    {{"name": "UPPERCASE_CODE", "group_name": "Physical|Chemical|Microbiological|Other", "reported_name": "Human name", "description": "description", "common_name": "alias", "analysis_type": "Chemical|Physical|Micro|Organoleptic|Calculated", "confidence": 0.9, "review_notes": null}}
  ],
  "components": [
    {{"analysis": "PARENT_ANALYSIS_CODE", "name": "component name", "num_replicates": 1, "order_number": 1, "result_type": "Numeric|Text|Pass/Fail", "units": "unit_code", "minimum": null, "maximum": null, "confidence": 0.9, "review_notes": null}}
  ],
  "units": [
    {{"unit_code": "PCT", "description": "Percentage", "display_string": "%", "group_name": null, "confidence": 0.95}}
  ],
  "products": [
    {{"name": "PRODUCT_CODE", "description": "description", "group_name": "group", "confidence": 0.9}}
  ],
  "product_specs": [
    {{"product": "PRODUCT_CODE", "sampling_point": null, "spec_type": "Release", "grade": null, "stage": "Finished Product", "analysis": "ANALYSIS_CODE", "reported_name": null, "description": null, "heading": null, "component": null, "units": null, "round": null, "place": null, "spec_rule": "Between|LessThan|GreaterThan|Text", "min_value": null, "max_value": null, "text_value": null, "class_": null, "file_name": null, "show_on_certificate": "Y", "c_stock": null, "rule_type": null, "confidence": 0.85, "review_notes": null}}
  ],
  "product_grades": [
    {{"description": "grade description", "continue_checking": null, "test_list": null, "always_check": null, "c_stp_no": null, "c_spec_no": null, "confidence": 0.8}}
  ],
  "prod_grade_stages": [
    {{"product": "PRODUCT_CODE", "sampling_point": null, "grade": null, "stage": null, "heading": null, "analysis": "ANALYSIS_CODE", "order_number": 1, "description": null, "spec_type": null, "num_reps": 1, "reported_name": null, "required": "Y", "test_location": null, "required_volume": null, "file_name": null, "confidence": 0.8, "review_notes": null}}
  ],
  "tph_sample_plans": [
    {{"name": "PLAN_CODE", "description": "description", "group_name": null, "confidence": 0.85}}
  ],
  "tph_sample_plan_entries": [
    {{"t_ph_sample_plan": "PLAN_CODE", "entry_code": null, "description": null, "order_number": 1, "spec_type": null, "stage": null, "algorithm": null, "log_sample": "Y", "create_inventory": "Y", "retained_sample": "N", "stability": "N", "initial_status": "Pending", "num_samples": 1, "quantity": null, "units": null, "sampling_point": null, "test_location": null, "confidence": 0.8}}
  ],
  "tph_item_codes": [
    {{"name": "ITEM_CODE", "description": null, "group_name": null, "display_as": null, "sample_plan": null, "site": null, "confidence": 0.8}}
  ],
  "tph_item_code_specs": [],
  "tph_item_code_supps": []
}}"""


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

    A 20-page document = ~5 chunks = 5 API calls total (vs 80+ before).
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

        # Prepend training context to the first chunk only (keeps subsequent
        # chunks uncluttered while still giving the model reference examples)
        self._training_context = training_context

        chunks = self._splitter.split_text(combined)
        logger.info("Extracting from %d chunks (1 API call each)", len(chunks))

        results: dict[str, list] = {
            "analysis": [], "components": [], "units": [], "products": [],
            "product_grades": [], "prod_grade_stages": [], "product_specs": [],
            "tph_item_codes": [], "tph_item_code_specs": [], "tph_item_code_supps": [],
            "tph_sample_plans": [], "tph_sample_plan_entries": [],
        }

        for i, chunk in enumerate(chunks):
            logger.info("Processing chunk %d/%d...", i + 1, len(chunks))
            # Inject training context into the first chunk only
            effective_chunk = (self._training_context + "\n\n" + chunk) if (i == 0 and self._training_context) else chunk
            chunk_results = self._extract_chunk(effective_chunk)
            for key in results:
                results[key].extend(chunk_results.get(key, []))

        # Deduplicate each entity type
        results["analysis"]         = self._dedup(results["analysis"],         lambda r: r.name)
        results["components"]       = self._dedup(results["components"],       lambda r: f"{r.analysis}::{r.name}")
        results["units"]            = self._dedup(results["units"],            lambda r: r.unit_code)
        results["products"]         = self._dedup(results["products"],         lambda r: r.name)
        results["tph_item_codes"]   = self._dedup(results["tph_item_codes"],   lambda r: r.name)
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

        return {
            "analysis":                _parse_records(data.get("analysis", []),                AnalysisRecord),
            "components":              _parse_records(data.get("components", []),              ComponentRecord),
            "units":                   _parse_records(data.get("units", []),                   UnitRecord),
            "products":                _parse_records(data.get("products", []),                ProductRecord),
            "product_grades":          _parse_records(data.get("product_grades", []),          ProductGradeRecord),
            "prod_grade_stages":       _parse_records(data.get("prod_grade_stages", []),       ProdGradeStageRecord),
            "product_specs":           _parse_records(data.get("product_specs", []),           ProductSpecRecord),
            "tph_item_codes":          _parse_records(data.get("tph_item_codes", []),          TPHItemCodeRecord),
            "tph_item_code_specs":     _parse_records(data.get("tph_item_code_specs", []),     TPHItemCodeSpecRecord),
            "tph_item_code_supps":     _parse_records(data.get("tph_item_code_supps", []),     TPHItemCodeSuppRecord),
            "tph_sample_plans":        _parse_records(data.get("tph_sample_plans", []),        TPHSamplePlanRecord),
            "tph_sample_plan_entries": _parse_records(data.get("tph_sample_plan_entries", []), TPHSamplePlanEntryRecord),
        }

    @staticmethod
    def _dedup(records: list, key_fn: Any) -> list:
        seen: dict = {}
        for r in records:
            k = key_fn(r)
            if k not in seen or r.confidence > seen[k].confidence:
                seen[k] = r
        return list(seen.values())
