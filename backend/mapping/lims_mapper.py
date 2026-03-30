"""
lims_mapper.py - Apply mapping rules and cross-reference resolution to
an ExtractionResult.

This module bridges raw LLM extraction output and the validated,
normalised data that feeds into Excel generation.
"""

from __future__ import annotations

import logging

from models.schemas import ExtractionResult
from .rules import MappingRuleEngine

logger = logging.getLogger(__name__)


class LIMSMapper:
    """
    Post-process an ExtractionResult by applying rule-based normalisation.

    Steps:
      1. Normalise unit codes
      2. Classify analysis types
      3. Normalise result types in components
      4. Resolve unit references in components
      5. Parse spec rule strings into numeric limits
      6. Filter sheets not applicable to the document type
    """

    def __init__(self) -> None:
        self._rules = MappingRuleEngine()

    def apply(self, result: ExtractionResult) -> ExtractionResult:
        """
        Mutate result in-place applying all mapping rules.

        Returns the same result object for fluent chaining.
        """
        logger.info("Applying mapping rules for document type: %s", result.document_type)

        # Unit normalisation
        result.units = self._rules.normalise_units(result.units)

        # Analysis type classification
        result.analysis = self._rules.classify_analysis_types(result.analysis)

        # Component result type normalisation
        result.components = self._rules.normalise_result_types(result.components)

        # Resolve unit references in components
        result.components = self._rules.resolve_unit_refs(result.components, result.units)

        # Parse spec rule strings
        result.product_specs = self._rules.parse_spec_limits(result.product_specs)

        # Auto-generate unit records for any units referenced but not listed
        self._ensure_units_present(result)

        # Order numbering: fill in sequential order numbers if missing
        self._auto_order_numbers(result)

        logger.info("Mapping complete. Record counts: %s", result.record_count())
        return result

    # ── Private helpers ───────────────────────────────────────────────────

    def _ensure_units_present(self, result: ExtractionResult) -> None:
        """
        Auto-create Unit records for any unit code referenced in components
        or specs that doesn't have a corresponding Units row.
        """
        from models.schemas import UnitRecord

        existing_codes = {u.unit_code.upper() for u in result.units}
        referenced_codes: set[str] = set()

        for comp in result.components:
            if comp.units:
                referenced_codes.add(comp.units.upper())
        for spec in result.product_specs:
            if spec.units:
                referenced_codes.add(spec.units.upper())

        for code in referenced_codes - existing_codes:
            logger.debug("Auto-creating Unit record for code: %s", code)
            result.units.append(
                UnitRecord(
                    unit_code=code,
                    description=code,
                    display_string=code,
                    confidence=0.5,
                    review_notes="Auto-generated from component/spec reference",
                )
            )

    @staticmethod
    def _auto_order_numbers(result: ExtractionResult) -> None:
        """Fill sequential order numbers for records missing them."""
        for i, rec in enumerate(result.components, start=1):
            if rec.order_number is None:
                rec.order_number = i
        for i, rec in enumerate(result.prod_grade_stages, start=1):
            if rec.order_number is None:
                rec.order_number = i
        for i, rec in enumerate(result.tph_sample_plan_entries, start=1):
            if rec.order_number is None:
                rec.order_number = i
        for i, rec in enumerate(result.tph_item_code_specs, start=1):
            if rec.order_number is None:
                rec.order_number = i
        for i, rec in enumerate(result.tph_item_code_supps, start=1):
            if rec.order_number is None:
                rec.order_number = i
