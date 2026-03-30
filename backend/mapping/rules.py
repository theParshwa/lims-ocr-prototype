"""
rules.py - Rule-based post-processing engine for extracted LIMS entities.

Applies configurable normalisation rules AFTER the LLM extraction to:
  - Standardise unit codes
  - Classify analysis types by keyword matching
  - Normalise result types
  - Parse limit strings (NMT, NLT, between) into min/max values
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import yaml

from models.schemas import (
    AnalysisRecord,
    ComponentRecord,
    ProductSpecRecord,
    UnitRecord,
)

logger = logging.getLogger(__name__)

_RULES_PATH = Path(__file__).parent / "config" / "mapping_rules.yaml"


class MappingRuleEngine:
    """Apply deterministic mapping rules to extracted LIMS records."""

    def __init__(self, rules_path: str | Path = _RULES_PATH) -> None:
        with open(rules_path, encoding="utf-8") as fh:
            self._rules: dict = yaml.safe_load(fh)

        self._unit_map: dict[str, str] = {
            k.lower(): v
            for k, v in self._rules.get("unit_normalisation", {}).items()
        }
        self._analysis_types: dict[str, list[str]] = self._rules.get("analysis_types", {})
        self._result_types: dict[str, list[str]] = self._rules.get("result_types", {})

    # ── Public API ────────────────────────────────────────────────────────

    def normalise_units(self, records: list[UnitRecord]) -> list[UnitRecord]:
        """Normalise unit_code values using the lookup table."""
        for rec in records:
            normalised = self._unit_map.get(rec.unit_code.lower())
            if normalised:
                rec.unit_code = normalised
        return records

    def classify_analysis_types(self, records: list[AnalysisRecord]) -> list[AnalysisRecord]:
        """Fill in missing analysis_type by matching keywords."""
        for rec in records:
            if not rec.analysis_type:
                rec.analysis_type = self._detect_analysis_type(rec.name + " " + (rec.description or ""))
        return records

    def normalise_result_types(self, records: list[ComponentRecord]) -> list[ComponentRecord]:
        """Normalise result_type fields."""
        for rec in records:
            if rec.result_type:
                rec.result_type = self._detect_result_type(rec.result_type)
            elif rec.units in ("CFUG", "CFUML"):
                rec.result_type = "Numeric"
        return records

    def parse_spec_limits(self, specs: list[ProductSpecRecord]) -> list[ProductSpecRecord]:
        """Parse text-based limit descriptions into numeric min/max."""
        for spec in specs:
            if spec.spec_rule:
                self._apply_spec_rule(spec)
        return specs

    def resolve_unit_refs(
        self,
        components: list[ComponentRecord],
        units: list[UnitRecord],
    ) -> list[ComponentRecord]:
        """Map component unit strings to canonical unit codes in the units sheet."""
        known_codes = {u.unit_code.lower() for u in units}
        for comp in components:
            if comp.units:
                normalised = self._unit_map.get(comp.units.lower(), comp.units.upper())
                comp.units = normalised
        return components

    def get_applicable_sheets(self, document_type: str) -> list[str]:
        """Return which sheets should be populated for the given document type."""
        sheet_map = self._rules.get("document_type_sheets", {})
        return sheet_map.get(document_type.upper(), sheet_map.get("OTHER", []))

    # ── Private helpers ───────────────────────────────────────────────────

    def _detect_analysis_type(self, text: str) -> str:
        text_lower = text.lower()
        for atype, keywords in self._analysis_types.items():
            for kw in keywords:
                if kw.lower() in text_lower:
                    return atype
        return "Chemical"  # sensible default

    def _detect_result_type(self, text: str) -> str:
        text_lower = text.lower()
        for rtype, keywords in self._result_types.items():
            for kw in keywords:
                if kw.lower() in text_lower:
                    return rtype
        return "Numeric"

    @staticmethod
    def _apply_spec_rule(spec: ProductSpecRecord) -> None:
        """Parse the spec_rule string to populate min/max/text_value."""
        rule = spec.spec_rule or ""

        # Between pattern: "10 - 50" or "10 to 50"
        between = re.search(r"(\d+\.?\d*)\s*[-–to]+\s*(\d+\.?\d*)", rule)
        if between:
            spec.min_value = spec.min_value or float(between.group(1))
            spec.max_value = spec.max_value or float(between.group(2))
            spec.spec_rule = "Between"
            return

        # Less than: NMT, ≤, max
        lt = re.search(r"(?:NMT|≤|<=|max(?:imum)?)\s*(\d+\.?\d*)", rule, re.IGNORECASE)
        if lt:
            spec.max_value = spec.max_value or float(lt.group(1))
            spec.spec_rule = "LessThan"
            return

        # Greater than: NLT, ≥, min
        gt = re.search(r"(?:NLT|≥|>=|min(?:imum)?)\s*(\d+\.?\d*)", rule, re.IGNORECASE)
        if gt:
            spec.min_value = spec.min_value or float(gt.group(1))
            spec.spec_rule = "GreaterThan"
            return

        # Text conformance
        text_patterns = ["conforms", "absent", "not detected", r"\bND\b", "pass"]
        for pattern in text_patterns:
            if re.search(pattern, rule, re.IGNORECASE):
                spec.text_value = spec.text_value or rule
                spec.spec_rule = "Text"
                return
