"""
schemas.py - Pydantic v2 schemas for every LIMS Load Sheet row type.

Each model mirrors one Excel sheet exactly. Optional fields map to columns
that may not be present in every document type. The `confidence` and `notes`
fields are internal quality-control annotations; they are stripped before
Excel export.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


# ── Confidence helper ─────────────────────────────────────────────────────────

class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


def _confidence_level(score: float) -> ConfidenceLevel:
    if score >= 0.85:
        return ConfidenceLevel.HIGH
    if score >= 0.6:
        return ConfidenceLevel.MEDIUM
    return ConfidenceLevel.LOW


class _Annotated(BaseModel):
    """Mixin that adds AI quality-control fields to every record."""

    confidence: float = Field(default=1.0, ge=0.0, le=1.0, exclude=True)
    confidence_level: Optional[ConfidenceLevel] = Field(default=None, exclude=True)
    review_notes: Optional[str] = Field(default=None, exclude=True)
    source_text: Optional[str] = Field(default=None, exclude=True)

    @model_validator(mode="after")
    def _set_confidence_level(self) -> "_Annotated":
        self.confidence_level = _confidence_level(self.confidence)
        return self


# ── Analysis Sheet ────────────────────────────────────────────────────────────

class AnalysisRecord(_Annotated):
    """One row in the Analysis sheet."""

    name: str = Field(..., description="Unique analysis identifier / code")
    group_name: Optional[str] = Field(None, description="Analysis group")
    reported_name: Optional[str] = Field(None, description="Name shown on report")
    description: Optional[str] = Field(None, description="Long description")
    common_name: Optional[str] = Field(None, description="Common / alias name")
    analysis_type: Optional[str] = Field(None, description="Type: Chemical, Physical, Micro, etc.")


# ── Component Sheet ───────────────────────────────────────────────────────────

class ComponentRecord(_Annotated):
    """One row in the Component sheet."""

    analysis: str = Field(..., description="Foreign key → Analysis.name")
    name: str = Field(..., description="Component / parameter name")
    num_replicates: Optional[int] = Field(None, ge=1)
    order_number: Optional[int] = Field(None, ge=0)
    result_type: Optional[str] = Field(None, description="Numeric, Text, Boolean, etc.")
    units: Optional[str] = Field(None, description="Unit code → Units sheet")
    minimum: Optional[float] = None
    maximum: Optional[float] = None


# ── Units Sheet ───────────────────────────────────────────────────────────────

class UnitRecord(_Annotated):
    """One row in the Units sheet."""

    unit_code: str = Field(..., description="Short unit code, e.g. PCT, MGKG")
    description: Optional[str] = None
    display_string: Optional[str] = Field(None, description="Rendered string, e.g. '%', 'mg/kg'")
    group_name: Optional[str] = None


# ── Product Sheet ─────────────────────────────────────────────────────────────

class ProductRecord(_Annotated):
    """One row in the Product sheet."""

    name: str
    description: Optional[str] = None
    group_name: Optional[str] = None


# ── Product Grade Sheet ───────────────────────────────────────────────────────

class ProductGradeRecord(_Annotated):
    """One row in the Product Grade sheet."""

    description: str
    continue_checking: Optional[str] = None
    test_list: Optional[str] = None
    always_check: Optional[str] = None
    c_stp_no: Optional[str] = Field(None, alias="C STP NO")
    c_spec_no: Optional[str] = Field(None, alias="C Spec No")

    model_config = {"populate_by_name": True}


# ── Prod Grade Stage Sheet ────────────────────────────────────────────────────

class ProdGradeStageRecord(_Annotated):
    """One row in the Prod Grade Stage sheet."""

    product: str
    sampling_point: Optional[str] = None
    grade: Optional[str] = None
    stage: Optional[str] = None
    heading: Optional[str] = None
    analysis: Optional[str] = None
    order_number: Optional[int] = None
    description: Optional[str] = None
    spec_type: Optional[str] = None
    num_reps: Optional[int] = None
    reported_name: Optional[str] = None
    required: Optional[str] = None
    test_location: Optional[str] = None
    required_volume: Optional[float] = None
    file_name: Optional[str] = None


# ── Product Spec Sheet ────────────────────────────────────────────────────────

class ProductSpecRecord(_Annotated):
    """One row in the Product Spec sheet."""

    product: str
    sampling_point: Optional[str] = None
    spec_type: Optional[str] = None
    grade: Optional[str] = None
    stage: Optional[str] = None
    analysis: Optional[str] = None
    reported_name: Optional[str] = None
    description: Optional[str] = None
    heading: Optional[str] = None
    component: Optional[str] = None
    units: Optional[str] = None
    round: Optional[int] = None
    place: Optional[int] = None
    spec_rule: Optional[str] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    text_value: Optional[str] = None
    class_: Optional[str] = Field(None, alias="class")
    file_name: Optional[str] = None
    show_on_certificate: Optional[str] = None
    c_stock: Optional[str] = None
    rule_type: Optional[str] = None

    model_config = {"populate_by_name": True}


# ── T PH Item Code Sheet ──────────────────────────────────────────────────────

class TPHItemCodeRecord(_Annotated):
    """One row in the T PH ITEM CODE sheet."""

    name: str
    description: Optional[str] = None
    group_name: Optional[str] = None
    display_as: Optional[str] = None
    sample_plan: Optional[str] = None
    site: Optional[str] = None


# ── T PH Item Code Spec Sheet ─────────────────────────────────────────────────

class TPHItemCodeSpecRecord(_Annotated):
    """One row in the T PH ITEM CODE Spec sheet."""

    t_ph_item_code: str = Field(..., alias="T PH Item Code")
    spec_code: Optional[str] = None
    product_spec: Optional[str] = None
    spec_class: Optional[str] = None
    order_number: Optional[int] = None
    grade: Optional[str] = None

    model_config = {"populate_by_name": True}


# ── T PH Item Code Supp Sheet ─────────────────────────────────────────────────

class TPHItemCodeSuppRecord(_Annotated):
    """One row in the T PH ITEM CODE SUPP sheet."""

    t_ph_item_code: str = Field(..., alias="T PH Item Code")
    supplier: Optional[str] = None
    active: Optional[str] = None
    status_1: Optional[str] = None
    status_2: Optional[str] = None
    order_number: Optional[int] = None
    retest_interval: Optional[int] = None
    expiry_interval: Optional[int] = None
    full_test_frequency: Optional[int] = None
    lots_to_go: Optional[int] = None
    date_last_tested: Optional[str] = None

    model_config = {"populate_by_name": True}


# ── T PH Sample Plan Sheet ────────────────────────────────────────────────────

class TPHSamplePlanRecord(_Annotated):
    """One row in the T PH SAMPLE PLAN sheet."""

    name: str
    description: Optional[str] = None
    group_name: Optional[str] = None


# ── T PH Sample Plan Entry Sheet ─────────────────────────────────────────────

class TPHSamplePlanEntryRecord(_Annotated):
    """One row in the T PH SAMPLE PLAN Entry sheet."""

    t_ph_sample_plan: str = Field(..., alias="T PH Sample Plan")
    entry_code: Optional[str] = None
    description: Optional[str] = None
    order_number: Optional[int] = None
    spec_type: Optional[str] = None
    stage: Optional[str] = None
    algorithm: Optional[str] = None
    log_sample: Optional[str] = None
    create_inventory: Optional[str] = None
    retained_sample: Optional[str] = None
    stability: Optional[str] = None
    initial_status: Optional[str] = None
    num_samples: Optional[int] = None
    quantity: Optional[float] = None
    units: Optional[str] = None
    sampling_point: Optional[str] = None
    test_location: Optional[str] = None

    model_config = {"populate_by_name": True}


# ── Top-level job/extraction models ──────────────────────────────────────────

class JobStatus(str, Enum):
    PENDING = "pending"
    EXTRACTING = "extracting"
    MAPPING = "mapping"
    VALIDATING = "validating"
    COMPLETE = "complete"
    FAILED = "failed"


class ValidationError(BaseModel):
    sheet: str
    row_index: Optional[int] = None
    field: str
    message: str
    severity: Literal["error", "warning"] = "error"


class ExtractionResult(BaseModel):
    """Complete extraction payload returned to the frontend."""

    job_id: str = Field(default_factory=lambda: str(uuid4()))
    document_type: str = "unknown"
    document_name: str = ""
    status: JobStatus = JobStatus.PENDING
    progress: int = Field(default=0, ge=0, le=100)
    message: str = ""

    # Sheet data
    analysis: list[AnalysisRecord] = Field(default_factory=list)
    components: list[ComponentRecord] = Field(default_factory=list)
    units: list[UnitRecord] = Field(default_factory=list)
    products: list[ProductRecord] = Field(default_factory=list)
    product_grades: list[ProductGradeRecord] = Field(default_factory=list)
    prod_grade_stages: list[ProdGradeStageRecord] = Field(default_factory=list)
    product_specs: list[ProductSpecRecord] = Field(default_factory=list)
    tph_item_codes: list[TPHItemCodeRecord] = Field(default_factory=list)
    tph_item_code_specs: list[TPHItemCodeSpecRecord] = Field(default_factory=list)
    tph_item_code_supps: list[TPHItemCodeSuppRecord] = Field(default_factory=list)
    tph_sample_plans: list[TPHSamplePlanRecord] = Field(default_factory=list)
    tph_sample_plan_entries: list[TPHSamplePlanEntryRecord] = Field(default_factory=list)

    # Quality control
    validation_errors: list[dict[str, Any]] = Field(default_factory=list)
    audit_log: list[dict[str, Any]] = Field(default_factory=list)
    overall_confidence: float = 0.0

    def record_count(self) -> dict[str, int]:
        return {
            "analysis": len(self.analysis),
            "components": len(self.components),
            "units": len(self.units),
            "products": len(self.products),
            "product_grades": len(self.product_grades),
            "prod_grade_stages": len(self.prod_grade_stages),
            "product_specs": len(self.product_specs),
            "tph_item_codes": len(self.tph_item_codes),
            "tph_item_code_specs": len(self.tph_item_code_specs),
            "tph_item_code_supps": len(self.tph_item_code_supps),
            "tph_sample_plans": len(self.tph_sample_plans),
            "tph_sample_plan_entries": len(self.tph_sample_plan_entries),
        }


class DocumentJob(BaseModel):
    """Lightweight job descriptor stored in the database."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    filename: str
    original_filename: str
    file_path: str
    status: JobStatus = JobStatus.PENDING
    document_type: str = "unknown"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    error_message: Optional[str] = None
    output_path: Optional[str] = None
