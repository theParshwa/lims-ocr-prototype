"""
test_validation.py - Tests for schema and cross-reference validators.
"""

import pytest

from models.schemas import (
    AnalysisRecord,
    ComponentRecord,
    ExtractionResult,
    ProductRecord,
    ProductSpecRecord,
)
from validation.schema_validator import SchemaValidator
from validation.cross_ref_validator import CrossRefValidator


def _base_result(**kwargs) -> ExtractionResult:
    return ExtractionResult(job_id="test", document_name="test.pdf", **kwargs)


class TestSchemaValidator:
    def setup_method(self):
        self.validator = SchemaValidator()

    def test_no_errors_on_valid_data(self):
        result = _base_result(
            analysis=[AnalysisRecord(name="MOISTURE", analysis_type="Chemical", confidence=0.9)],
            components=[ComponentRecord(analysis="MOISTURE", name="Value", confidence=0.9)],
        )
        issues = self.validator.validate(result)
        assert not any(i.severity == "error" for i in issues)

    def test_missing_analysis_name(self):
        result = _base_result(
            analysis=[AnalysisRecord(name="", confidence=0.9)],
        )
        issues = self.validator.validate(result)
        errors = [i for i in issues if i.severity == "error" and i.field == "name"]
        assert len(errors) >= 1

    def test_component_min_greater_than_max(self):
        result = _base_result(
            components=[
                ComponentRecord(analysis="MOISTURE", name="Value", minimum=10.0, maximum=5.0)
            ],
        )
        issues = self.validator.validate(result)
        min_errors = [i for i in issues if i.field == "minimum" and i.severity == "error"]
        assert len(min_errors) >= 1

    def test_low_confidence_flagged_as_warning(self):
        result = _base_result(
            analysis=[AnalysisRecord(name="UNKNOWN_TEST", confidence=0.3)],
        )
        issues = self.validator.validate(result)
        warnings = [i for i in issues if i.severity == "warning" and i.field == "confidence"]
        assert len(warnings) >= 1

    def test_duplicate_unit_codes(self):
        from models.schemas import UnitRecord
        result = _base_result(
            units=[
                UnitRecord(unit_code="PCT"),
                UnitRecord(unit_code="PCT"),  # duplicate
            ],
        )
        issues = self.validator.validate(result)
        dup_warnings = [i for i in issues if "Duplicate" in i.message]
        assert len(dup_warnings) >= 1


class TestCrossRefValidator:
    def setup_method(self):
        self.validator = CrossRefValidator()

    def test_valid_cross_references(self):
        result = _base_result(
            analysis=[AnalysisRecord(name="MOISTURE")],
            products=[ProductRecord(product="PRODUCT_A")],
            components=[ComponentRecord(analysis="MOISTURE", name="Value")],
            product_specs=[
                ProductSpecRecord(product="PRODUCT_A", analysis="MOISTURE")
            ],
        )
        issues = self.validator.validate(result)
        assert len(issues) == 0

    def test_component_referencing_nonexistent_analysis(self):
        result = _base_result(
            analysis=[],  # No analyses
            components=[ComponentRecord(analysis="NONEXISTENT", name="Value")],
        )
        issues = self.validator.validate(result)
        fk_issues = [i for i in issues if "not found" in i.message and i.field == "analysis"]
        assert len(fk_issues) >= 1

    def test_spec_referencing_nonexistent_product(self):
        result = _base_result(
            products=[],
            product_specs=[ProductSpecRecord(product="GHOST_PRODUCT", analysis="MOISTURE")],
        )
        issues = self.validator.validate(result)
        fk_issues = [i for i in issues if "not found" in i.message and i.field == "product"]
        assert len(fk_issues) >= 1
