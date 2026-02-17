"""
schema_validator.py - Validate each record against required field rules.

Returns a list of ValidationIssue objects describing errors and warnings.
Does NOT modify the data – purely informational.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Literal

from models.schemas import ExtractionResult

logger = logging.getLogger(__name__)


@dataclass
class ValidationIssue:
    sheet: str
    row_index: int
    field: str
    message: str
    severity: Literal["error", "warning"] = "error"

    def to_dict(self) -> dict[str, Any]:
        return {
            "sheet": self.sheet,
            "row_index": self.row_index,
            "field": self.field,
            "message": self.message,
            "severity": self.severity,
        }


class SchemaValidator:
    """Field-level validation for all LIMS Load Sheet records."""

    def validate(self, result: ExtractionResult) -> list[ValidationIssue]:
        """Validate all sheets and return collected issues."""
        issues: list[ValidationIssue] = []
        issues.extend(self._validate_analysis(result))
        issues.extend(self._validate_components(result))
        issues.extend(self._validate_units(result))
        issues.extend(self._validate_products(result))
        issues.extend(self._validate_product_specs(result))
        issues.extend(self._validate_prod_grade_stages(result))
        issues.extend(self._validate_sample_plans(result))
        return issues

    # ── Per-sheet validators ──────────────────────────────────────────────

    def _validate_analysis(self, result: ExtractionResult) -> list[ValidationIssue]:
        issues = []
        for i, rec in enumerate(result.analysis):
            if not rec.name:
                issues.append(ValidationIssue("Analysis", i, "name", "Name is required", "error"))
            elif " " in rec.name:
                issues.append(ValidationIssue(
                    "Analysis", i, "name",
                    f"Name '{rec.name}' contains spaces – use underscores or codes",
                    "warning",
                ))
            if rec.confidence < 0.6:
                issues.append(ValidationIssue(
                    "Analysis", i, "confidence",
                    f"Low confidence ({rec.confidence:.0%}): {rec.review_notes or 'review required'}",
                    "warning",
                ))
        return issues

    def _validate_components(self, result: ExtractionResult) -> list[ValidationIssue]:
        issues = []
        for i, rec in enumerate(result.components):
            if not rec.name:
                issues.append(ValidationIssue("Component", i, "name", "Name is required"))
            if not rec.analysis:
                issues.append(ValidationIssue("Component", i, "analysis", "Analysis FK is required"))
            if rec.minimum is not None and rec.maximum is not None:
                if rec.minimum > rec.maximum:
                    issues.append(ValidationIssue(
                        "Component", i, "minimum",
                        f"Minimum ({rec.minimum}) > Maximum ({rec.maximum})",
                    ))
            if rec.num_replicates is not None and rec.num_replicates < 1:
                issues.append(ValidationIssue(
                    "Component", i, "num_replicates",
                    "Num Replicates must be ≥ 1",
                ))
            if rec.confidence < 0.6:
                issues.append(ValidationIssue(
                    "Component", i, "confidence",
                    f"Low confidence ({rec.confidence:.0%})",
                    "warning",
                ))
        return issues

    def _validate_units(self, result: ExtractionResult) -> list[ValidationIssue]:
        issues = []
        seen: set[str] = set()
        for i, rec in enumerate(result.units):
            if not rec.unit_code:
                issues.append(ValidationIssue("Units", i, "unit_code", "Unit Code is required"))
            elif rec.unit_code in seen:
                issues.append(ValidationIssue(
                    "Units", i, "unit_code",
                    f"Duplicate unit code: {rec.unit_code}",
                    "warning",
                ))
            seen.add(rec.unit_code)
        return issues

    def _validate_products(self, result: ExtractionResult) -> list[ValidationIssue]:
        issues = []
        for i, rec in enumerate(result.products):
            if not rec.name:
                issues.append(ValidationIssue("Product", i, "name", "Name is required"))
        return issues

    def _validate_product_specs(self, result: ExtractionResult) -> list[ValidationIssue]:
        issues = []
        for i, spec in enumerate(result.product_specs):
            if not spec.product:
                issues.append(ValidationIssue("Product Spec", i, "product", "Product is required"))
            if spec.min_value is not None and spec.max_value is not None:
                if spec.min_value > spec.max_value:
                    issues.append(ValidationIssue(
                        "Product Spec", i, "min_value",
                        f"Min ({spec.min_value}) > Max ({spec.max_value})",
                    ))
            if spec.confidence < 0.6:
                issues.append(ValidationIssue(
                    "Product Spec", i, "confidence",
                    f"Low confidence ({spec.confidence:.0%}): {spec.review_notes or ''}",
                    "warning",
                ))
        return issues

    def _validate_prod_grade_stages(self, result: ExtractionResult) -> list[ValidationIssue]:
        issues = []
        for i, rec in enumerate(result.prod_grade_stages):
            if not rec.product:
                issues.append(ValidationIssue("Prod Grade Stage", i, "product", "Product is required"))
        return issues

    def _validate_sample_plans(self, result: ExtractionResult) -> list[ValidationIssue]:
        issues = []
        plan_names = {p.name for p in result.tph_sample_plans}
        for i, entry in enumerate(result.tph_sample_plan_entries):
            if not entry.t_ph_sample_plan:
                issues.append(ValidationIssue(
                    "T PH Sample Plan Entry", i, "t_ph_sample_plan", "Plan name is required"
                ))
        return issues
