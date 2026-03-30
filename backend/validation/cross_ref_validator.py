"""
cross_ref_validator.py - Cross-sheet referential integrity validation.

Checks foreign key relationships:
  - Component.analysis → Analysis.name
  - ProductSpec.analysis → Analysis.name
  - ProductSpec.product  → Product.name
  - ProdGradeStage.product → Product.name
  - ProdGradeStage.analysis → Analysis.name
  - TPHItemCodeSpec.t_ph_item_code → TPHItemCode.name
  - TPHSamplePlanEntry.t_ph_sample_plan → TPHSamplePlan.name
"""

from __future__ import annotations

import logging
from typing import Any

from models.schemas import ExtractionResult
from .schema_validator import ValidationIssue

logger = logging.getLogger(__name__)


class CrossRefValidator:
    """Validate cross-sheet foreign key references."""

    def validate(self, result: ExtractionResult) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        analysis_names = {r.name for r in result.analysis}
        product_names = {r.product for r in result.products}
        unit_codes = {r.unit_code for r in result.units}
        item_code_names = {r.t_ph_item_code for r in result.tph_item_codes}
        plan_names = {r.name for r in result.tph_sample_plans}

        # Component → Analysis
        for i, comp in enumerate(result.components):
            if comp.analysis and comp.analysis not in analysis_names:
                issues.append(ValidationIssue(
                    "COMPONENT", i, "analysis",
                    f"Analysis '{comp.analysis}' not found in Analysis sheet",
                    "warning",  # warning, not error – LLM may have found it in context
                ))
            if comp.units and comp.units not in unit_codes:
                issues.append(ValidationIssue(
                    "COMPONENT", i, "units",
                    f"Unit code '{comp.units}' not found in Units sheet",
                    "warning",
                ))

        # ProductSpec → Product + Analysis
        for i, spec in enumerate(result.product_specs):
            if spec.product and spec.product not in product_names:
                issues.append(ValidationIssue(
                    "PRODUCT_SPEC", i, "product",
                    f"Product '{spec.product}' not found in Product sheet",
                    "warning",
                ))
            if spec.analysis and spec.analysis not in analysis_names:
                issues.append(ValidationIssue(
                    "PRODUCT_SPEC", i, "analysis",
                    f"Analysis '{spec.analysis}' not found in Analysis sheet",
                    "warning",
                ))

        # ProdGradeStage → Product + Analysis
        for i, pgs in enumerate(result.prod_grade_stages):
            if pgs.product and pgs.product not in product_names:
                issues.append(ValidationIssue(
                    "PROD_GRADE_STAGE", i, "product",
                    f"Product '{pgs.product}' not found in Product sheet",
                    "warning",
                ))
            if pgs.analysis and pgs.analysis not in analysis_names:
                issues.append(ValidationIssue(
                    "PROD_GRADE_STAGE", i, "analysis",
                    f"Analysis '{pgs.analysis}' not found in Analysis sheet",
                    "warning",
                ))

        # TPHItemCodeSpec → TPHItemCode
        for i, spec in enumerate(result.tph_item_code_specs):
            code = spec.t_ph_item_code
            if code and code not in item_code_names:
                issues.append(ValidationIssue(
                    "T_PH_ITEM_CODE_SPEC", i, "t_ph_item_code",
                    f"Item code '{code}' not found in T PH ITEM CODE sheet",
                    "warning",
                ))

        # TPHSamplePlanEntry → TPHSamplePlan
        for i, entry in enumerate(result.tph_sample_plan_entries):
            plan = entry.t_ph_sample_plan
            if plan and plan not in plan_names:
                issues.append(ValidationIssue(
                    "T_PH_SAMPLE_PLAN_EN", i, "t_ph_sample_plan",
                    f"Sample plan '{plan}' not found in T PH SAMPLE PLAN sheet",
                    "warning",
                ))

        logger.info(
            "Cross-reference validation: %d issues found (%d errors, %d warnings)",
            len(issues),
            sum(1 for i in issues if i.severity == "error"),
            sum(1 for i in issues if i.severity == "warning"),
        )
        return issues
