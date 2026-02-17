"""
test_mapping.py - Tests for the LIMS mapping rule engine.
"""

import pytest

from models.schemas import (
    AnalysisRecord,
    ComponentRecord,
    ProductSpecRecord,
    UnitRecord,
)


class TestMappingRuleEngine:
    @pytest.fixture
    def engine(self):
        from mapping.rules import MappingRuleEngine
        return MappingRuleEngine()

    def test_unit_normalisation_percent(self, engine):
        units = [UnitRecord(unit_code="%", confidence=0.9)]
        result = engine.normalise_units(units)
        assert result[0].unit_code == "PCT"

    def test_unit_normalisation_ppm(self, engine):
        units = [UnitRecord(unit_code="ppm", confidence=0.9)]
        result = engine.normalise_units(units)
        assert result[0].unit_code == "MGKG"

    def test_unit_normalisation_unknown_unchanged(self, engine):
        units = [UnitRecord(unit_code="CUSTOM_UNIT", confidence=0.9)]
        result = engine.normalise_units(units)
        assert result[0].unit_code == "CUSTOM_UNIT"

    def test_analysis_type_chemical(self, engine):
        records = [AnalysisRecord(name="MOISTURE_TEST", description="Moisture content determination")]
        result = engine.classify_analysis_types(records)
        assert result[0].analysis_type == "Chemical"

    def test_analysis_type_micro(self, engine):
        records = [AnalysisRecord(name="TPC", description="Total Plate Count microbiological test")]
        result = engine.classify_analysis_types(records)
        assert result[0].analysis_type == "Microbiological"

    def test_analysis_type_physical(self, engine):
        records = [AnalysisRecord(name="VISCOSITY", description="Viscosity measurement")]
        result = engine.classify_analysis_types(records)
        assert result[0].analysis_type == "Physical"

    def test_parse_spec_limits_between(self, engine):
        spec = ProductSpecRecord(product="PROD_A", spec_rule="5.0 - 7.0")
        result = engine.parse_spec_limits([spec])
        assert result[0].min_value == 5.0
        assert result[0].max_value == 7.0
        assert result[0].spec_rule == "Between"

    def test_parse_spec_limits_less_than(self, engine):
        spec = ProductSpecRecord(product="PROD_A", spec_rule="NMT 10")
        result = engine.parse_spec_limits([spec])
        assert result[0].max_value == 10.0
        assert result[0].spec_rule == "LessThan"

    def test_parse_spec_limits_greater_than(self, engine):
        spec = ProductSpecRecord(product="PROD_A", spec_rule="NLT 95")
        result = engine.parse_spec_limits([spec])
        assert result[0].min_value == 95.0
        assert result[0].spec_rule == "GreaterThan"

    def test_parse_spec_limits_text_conforms(self, engine):
        spec = ProductSpecRecord(product="PROD_A", spec_rule="Conforms to specification")
        result = engine.parse_spec_limits([spec])
        assert result[0].spec_rule == "Text"

    def test_applicable_sheets_stp(self, engine):
        sheets = engine.get_applicable_sheets("STP")
        assert "analysis" in sheets
        assert "components" in sheets
        assert "product_specs" in sheets

    def test_applicable_sheets_ptp(self, engine):
        sheets = engine.get_applicable_sheets("PTP")
        assert "tph_item_codes" in sheets
        assert "tph_sample_plans" in sheets

    def test_result_type_numeric(self, engine):
        comps = [ComponentRecord(analysis="MOISTURE", name="Value", result_type="numeric value")]
        result = engine.normalise_result_types(comps)
        assert result[0].result_type == "Numeric"


class TestLIMSMapper:
    def test_auto_creates_missing_units(self):
        from mapping.lims_mapper import LIMSMapper
        from models.schemas import ExtractionResult

        result = ExtractionResult(
            job_id="test-job",
            document_name="test.pdf",
            document_type="STP",
            components=[
                ComponentRecord(analysis="MOISTURE", name="Value", units="PCT")
            ],
            units=[],  # No units defined
        )
        mapper = LIMSMapper()
        mapped = mapper.apply(result)

        unit_codes = {u.unit_code for u in mapped.units}
        assert "PCT" in unit_codes

    def test_auto_order_numbers(self):
        from mapping.lims_mapper import LIMSMapper
        from models.schemas import ExtractionResult

        result = ExtractionResult(
            job_id="test-job",
            document_name="test.pdf",
            components=[
                ComponentRecord(analysis="A", name="C1"),
                ComponentRecord(analysis="A", name="C2"),
            ],
        )
        mapper = LIMSMapper()
        mapped = mapper.apply(result)
        assert mapped.components[0].order_number == 1
        assert mapped.components[1].order_number == 2
