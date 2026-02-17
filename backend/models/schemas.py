"""
schemas.py - Pydantic v2 schemas for every LIMS Load Sheet row type.

Each model mirrors one Excel sheet exactly, matching the standard LIMS Load Sheet
format with ~30 sheets. Optional fields map to columns that may not be present
in every document type. The `confidence` and `notes` fields are internal
quality-control annotations; they are stripped before Excel export.
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


# ══════════════════════════════════════════════════════════════════════════════
# Sheet models — ordered to match standard LIMS Load Sheet tab order
# ══════════════════════════════════════════════════════════════════════════════

# ── 1. ANALYSIS_TYPES ────────────────────────────────────────────────────────

class AnalysisTypeRecord(_Annotated):
    name: str = Field(..., description="Analysis type name (e.g. CHEMICAL, INSTRUMENT, MICRO)")
    description: Optional[str] = None
    group_name: Optional[str] = None


# ── 2. COMMON_NAME ───────────────────────────────────────────────────────────

class CommonNameRecord(_Annotated):
    name: str = Field(..., description="Common name code (e.g. LOD)")
    description: Optional[str] = Field(None, description="Full description (e.g. Loss on drying)")
    group_name: Optional[str] = None


# ── 3. ANALYSIS ──────────────────────────────────────────────────────────────

class AnalysisRecord(_Annotated):
    name: str = Field(..., description="Unique analysis identifier / code")
    version: Optional[str] = None
    group_name: Optional[str] = None
    active: Optional[str] = Field(None, description="T or F")
    reported_name: Optional[str] = None
    common_name: Optional[str] = None
    analysis_type: Optional[str] = None
    description: Optional[str] = None


# ── 4. COMPONENT ─────────────────────────────────────────────────────────────

class ComponentRecord(_Annotated):
    analysis: str = Field(..., description="Foreign key → Analysis.name")
    name: str = Field(..., description="Component / parameter name")
    num_replicates: Optional[int] = Field(None, ge=1)
    version: Optional[str] = None
    order_number: Optional[int] = Field(None, ge=0)
    result_type: Optional[str] = None
    units: Optional[str] = None
    minimum: Optional[float] = None
    maximum: Optional[float] = None


# ── 5. UNITS ─────────────────────────────────────────────────────────────────

class UnitRecord(_Annotated):
    unit_code: str = Field(..., description="Short unit code, e.g. PCT, MGKG")
    description: Optional[str] = None
    display_string: Optional[str] = None
    group_name: Optional[str] = None


# ── 6. PRODUCT ───────────────────────────────────────────────────────────────

class ProductRecord(_Annotated):
    product: str = Field(..., description="Product name/code")
    version: Optional[str] = None
    sampling_point: Optional[str] = None
    grade: Optional[str] = None
    order_number: Optional[int] = None
    description: Optional[str] = None
    continue_checking: Optional[str] = None
    test_list: Optional[str] = None
    always_check: Optional[str] = None
    t_ph_same_lot: Optional[str] = None
    t_ph_status1: Optional[str] = None
    t_ph_status2: Optional[str] = None
    t_ph_recert: Optional[str] = None
    t_usp_secondary: Optional[str] = None
    test_location: Optional[str] = None
    reqd_volume: Optional[str] = None
    aliquot_group: Optional[str] = None
    c_spec_variation: Optional[str] = None
    c_test_group: Optional[str] = None


# ── 7. T_PH_GRADE ───────────────────────────────────────────────────────────

class TPHGradeRecord(_Annotated):
    name: str
    description: Optional[str] = None
    group_name: Optional[str] = None
    active: Optional[str] = None
    code: Optional[str] = None


# ── 8. SAMPLING_POINT ────────────────────────────────────────────────────────

class SamplingPointRecord(_Annotated):
    name: str
    description: Optional[str] = None
    group_name: Optional[str] = None


# ── 9. PRODUCT_GRADE ─────────────────────────────────────────────────────────

class ProductGradeRecord(_Annotated):
    product: Optional[str] = None
    version: Optional[str] = None
    grade: Optional[str] = None
    order_number: Optional[int] = None
    description: Optional[str] = None
    continue_checking: Optional[str] = None
    test_list: Optional[str] = None
    always_check: Optional[str] = None


# ── 10. PROD_GRADE_STAGE ─────────────────────────────────────────────────────

class ProdGradeStageRecord(_Annotated):
    product: str
    version: Optional[str] = None
    sampling_point: Optional[str] = None
    grade: Optional[str] = None
    stage: Optional[str] = None
    analysis: Optional[str] = None
    order_number: Optional[int] = None
    description: Optional[str] = None
    spec_type: Optional[str] = None
    num_reps: Optional[int] = None
    partial: Optional[str] = None
    ext_link: Optional[str] = None
    reported_name: Optional[str] = None
    variation: Optional[str] = None
    required: Optional[str] = None


# ── 11. PRODUCT_SPEC ─────────────────────────────────────────────────────────

class ProductSpecRecord(_Annotated):
    product: str
    version: Optional[str] = None
    sampling_point: Optional[str] = None
    grade: Optional[str] = None
    stage: Optional[str] = None
    analysis: Optional[str] = None
    component: Optional[str] = None
    units: Optional[str] = None
    round: Optional[int] = None
    rule_type: Optional[str] = None
    spec_rule: Optional[str] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    text_value: Optional[str] = None
    class_: Optional[str] = Field(None, alias="class")
    required: Optional[str] = None

    model_config = {"populate_by_name": True}


# ── 12. T_PH_ITEM_CODE ──────────────────────────────────────────────────────

class TPHItemCodeRecord(_Annotated):
    t_ph_item_code: str
    supplier: Optional[str] = None
    active: Optional[str] = None
    status1: Optional[str] = None
    status2: Optional[str] = None
    order_number: Optional[int] = None
    retest_interval: Optional[int] = None
    expiry_interval: Optional[int] = None
    full_test_freq: Optional[int] = None
    lots_to_go: Optional[int] = None
    date_last_tested: Optional[str] = None


# ── 13. T_PH_ITEM_CODE_SPEC ─────────────────────────────────────────────────

class TPHItemCodeSpecRecord(_Annotated):
    spec_code: Optional[str] = None
    t_ph_item_code: str
    product_spec: Optional[str] = None
    spec_class: Optional[str] = None
    order_number: Optional[int] = None
    grade: Optional[str] = None
    common_grade: Optional[str] = None


# ── 14. T_PH_ITEM_CODE_SUPP ─────────────────────────────────────────────────

class TPHItemCodeSuppRecord(_Annotated):
    t_ph_item_code: str
    supplier: Optional[str] = None
    active: Optional[str] = None
    status1: Optional[str] = None
    status2: Optional[str] = None
    order_number: Optional[int] = None


# ── 15. T_PH_SAMPLE_PLAN ────────────────────────────────────────────────────

class TPHSamplePlanRecord(_Annotated):
    name: str
    version: Optional[str] = None
    active: Optional[str] = None
    description: Optional[str] = None
    group_name: Optional[str] = None


# ── 16. T_PH_SAMPLE_PLAN_EN ─────────────────────────────────────────────────

class TPHSamplePlanEntryRecord(_Annotated):
    t_ph_sample_plan: str
    entry_code: Optional[str] = None
    version: Optional[str] = None
    description: Optional[str] = None
    order_number: Optional[int] = None
    spec_type: Optional[str] = None
    spec_status: Optional[str] = None
    t_ph_sample_type: Optional[str] = None
    log_sample: Optional[str] = None
    create_inventory: Optional[str] = None
    retained_sample: Optional[str] = None
    stability: Optional[str] = None
    initial_status: Optional[str] = None
    indic_samples: Optional[int] = None
    quantity: Optional[float] = None
    units: Optional[str] = None
    c_reanalysis_qty: Optional[str] = None
    c_stm_quantity: Optional[str] = None


# ── 17. CUSTOMER ─────────────────────────────────────────────────────────────

class CustomerRecord(_Annotated):
    name: str
    group_name: Optional[str] = None
    description: Optional[str] = None
    company_name: Optional[str] = None
    address1: Optional[str] = None
    address2: Optional[str] = None
    address3: Optional[str] = None
    address4: Optional[str] = None
    address5: Optional[str] = None
    address6: Optional[str] = None
    fax_num: Optional[str] = None
    phone_num: Optional[str] = None
    contact: Optional[str] = None
    email_addr: Optional[str] = None


# ── 18. T_SITE ───────────────────────────────────────────────────────────────

class TSiteRecord(_Annotated):
    name: str
    description: Optional[str] = None
    group_name: Optional[str] = None
    parent_site: Optional[str] = None


# ── 19. T_PLANT ──────────────────────────────────────────────────────────────

class TPlantRecord(_Annotated):
    name: str
    description: Optional[str] = None
    group_name: Optional[str] = None
    site: Optional[str] = None
    personnel_smp_type: Optional[str] = None
    personnel_stage: Optional[str] = None
    personnel_spec_type: Optional[str] = None


# ── 20. T_SUITE ──────────────────────────────────────────────────────────────

class TSuiteRecord(_Annotated):
    name: str
    description: Optional[str] = None
    group_name: Optional[str] = None
    plant: Optional[str] = None
    visual_workflow: Optional[str] = None
    corrective_action: Optional[str] = None
    restrict_collection: Optional[str] = None


# ── 21. PROCESS_UNIT ─────────────────────────────────────────────────────────

class ProcessUnitRecord(_Annotated):
    name: str
    description: Optional[str] = None
    group_name: Optional[str] = None
    product_grade: Optional[str] = None
    sample_template: Optional[str] = None
    running: Optional[str] = None
    phase: Optional[str] = None
    default_phase: Optional[str] = None
    t_alternate_grade: Optional[str] = None
    t_corrective_action: Optional[str] = None
    t_suite: Optional[str] = None


# ── 22. PROC_SCHED_PARENT ────────────────────────────────────────────────────

class ProcSchedParentRecord(_Annotated):
    name: str
    first_day_of_week: Optional[str] = None
    treat_holidays_as: Optional[str] = None
    workstation: Optional[str] = None
    running: Optional[str] = None
    description: Optional[str] = None
    group_name: Optional[str] = None
    active_flag: Optional[str] = None
    version: Optional[str] = None
    t_site: Optional[str] = None


# ── 23. PROCESS_SCHEDULE ─────────────────────────────────────────────────────

class ProcessScheduleRecord(_Annotated):
    schedule_number: Optional[str] = None
    login_offset: Optional[str] = None
    schd_collect_time: Optional[str] = None
    unit: Optional[str] = None
    sampling_point: Optional[str] = None
    test_list: Optional[str] = None
    analyses: Optional[str] = None
    mon_collect: Optional[str] = None
    tue_collect: Optional[str] = None
    wed_collect: Optional[str] = None
    thu_collect: Optional[str] = None
    fri_collect: Optional[str] = None
    sat_collect: Optional[str] = None
    sun_collect: Optional[str] = None
    wk_1_collect: Optional[str] = None
    wk_2_collect: Optional[str] = None
    wk_3_collect: Optional[str] = None
    wk_4_collect: Optional[str] = None
    description: Optional[str] = None
    schedule_name: Optional[str] = None
    order_number: Optional[int] = None
    running: Optional[str] = None
    phase: Optional[str] = None
    sched_rule: Optional[str] = None
    wk_5_collect: Optional[str] = None
    day_collect: Optional[str] = None
    jan_collect: Optional[str] = None
    feb_collect: Optional[str] = None
    mar_collect: Optional[str] = None
    apr_collect: Optional[str] = None
    may_collect: Optional[str] = None
    jun_collect: Optional[str] = None
    jul_collect: Optional[str] = None
    aug_collect: Optional[str] = None
    sep_collect: Optional[str] = None
    oct_collect: Optional[str] = None
    nov_collect: Optional[str] = None
    dec_collect: Optional[str] = None
    days_ahead: Optional[str] = None
    r4_base_date: Optional[str] = None
    r4_days: Optional[str] = None
    version: Optional[str] = None
    spec_type: Optional[str] = None
    stage: Optional[str] = None
    t_composite_group: Optional[str] = None
    t_corrective_action: Optional[str] = None
    t_group_order: Optional[str] = None
    t_mon_type: Optional[str] = None
    t_sample_type: Optional[str] = None
    t_time_window: Optional[str] = None


# ── 24. LIST ─────────────────────────────────────────────────────────────────

class ListRecord(_Annotated):
    list_name: str = Field(..., alias="list", description="List category (e.g. INST_TYPE)")
    name: str = Field(..., description="Entry name")
    value: Optional[str] = None
    order_number: Optional[int] = None

    model_config = {"populate_by_name": True}


# ── 25. LIST_ENTRY ───────────────────────────────────────────────────────────

class ListEntryRecord(_Annotated):
    name: str
    group_name: Optional[str] = None
    description: Optional[str] = None


# ── 26. VENDOR ───────────────────────────────────────────────────────────────

class VendorRecord(_Annotated):
    name: str
    description: Optional[str] = None
    contact: Optional[str] = None
    company_name: Optional[str] = None
    address1: Optional[str] = None
    address2: Optional[str] = None
    address3: Optional[str] = None
    address4: Optional[str] = None
    address5: Optional[str] = None
    address6: Optional[str] = None
    fax_num: Optional[str] = None
    phone_num: Optional[str] = None
    group_name: Optional[str] = None


# ── 27. SUPPLIER ─────────────────────────────────────────────────────────────

class SupplierRecord(_Annotated):
    name: str
    description: Optional[str] = None
    contact: Optional[str] = None
    company_name: Optional[str] = None
    address1: Optional[str] = None
    address2: Optional[str] = None
    address3: Optional[str] = None
    address4: Optional[str] = None
    address5: Optional[str] = None
    address6: Optional[str] = None
    fax_num: Optional[str] = None
    phone_num: Optional[str] = None
    group_name: Optional[str] = None


# ── 28. INSTRUMENTS ──────────────────────────────────────────────────────────

class InstrumentRecord(_Annotated):
    name: str
    group_name: Optional[str] = None
    description: Optional[str] = None
    inst_group: Optional[str] = None
    vendor: Optional[str] = None
    on_line: Optional[str] = None
    serial_no: Optional[str] = None
    pm_date: Optional[str] = None
    pm_intv: Optional[str] = None
    calib_date: Optional[str] = None
    calib_intv: Optional[str] = None
    model_no: Optional[str] = None


# ── 29. LIMS_USERS ───────────────────────────────────────────────────────────

class LimsUserRecord(_Annotated):
    user_name: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    group_name: Optional[str] = None
    description: Optional[str] = None
    email_addr: Optional[str] = None
    is_role: Optional[str] = None
    uses_roles: Optional[str] = None
    language_prefix: Optional[str] = None
    t_site: Optional[str] = None
    location_lab: Optional[str] = None


# ── 30. VERSIONS ─────────────────────────────────────────────────────────────

class VersionRecord(_Annotated):
    table_name: Optional[str] = None
    version: Optional[str] = None
    description: Optional[str] = None


# ══════════════════════════════════════════════════════════════════════════════
# Top-level job/extraction models
# ══════════════════════════════════════════════════════════════════════════════

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


# All sheet keys used in ExtractionResult
SHEET_KEYS = [
    "analysis_types", "common_names", "analysis", "components", "units",
    "products", "tph_grades", "sampling_points", "product_grades",
    "prod_grade_stages", "product_specs", "tph_item_codes",
    "tph_item_code_specs", "tph_item_code_supps", "tph_sample_plans",
    "tph_sample_plan_entries", "customers", "t_sites", "t_plants",
    "t_suites", "process_units", "proc_sched_parents", "process_schedules",
    "lists", "list_entries", "vendors", "suppliers", "instruments",
    "lims_users", "versions",
]


class ExtractionResult(BaseModel):
    """Complete extraction payload returned to the frontend."""

    job_id: str = Field(default_factory=lambda: str(uuid4()))
    document_type: str = "unknown"
    document_name: str = ""
    status: JobStatus = JobStatus.PENDING
    progress: int = Field(default=0, ge=0, le=100)
    message: str = ""

    # Sheet data — all 30 sheets
    analysis_types: list[AnalysisTypeRecord] = Field(default_factory=list)
    common_names: list[CommonNameRecord] = Field(default_factory=list)
    analysis: list[AnalysisRecord] = Field(default_factory=list)
    components: list[ComponentRecord] = Field(default_factory=list)
    units: list[UnitRecord] = Field(default_factory=list)
    products: list[ProductRecord] = Field(default_factory=list)
    tph_grades: list[TPHGradeRecord] = Field(default_factory=list)
    sampling_points: list[SamplingPointRecord] = Field(default_factory=list)
    product_grades: list[ProductGradeRecord] = Field(default_factory=list)
    prod_grade_stages: list[ProdGradeStageRecord] = Field(default_factory=list)
    product_specs: list[ProductSpecRecord] = Field(default_factory=list)
    tph_item_codes: list[TPHItemCodeRecord] = Field(default_factory=list)
    tph_item_code_specs: list[TPHItemCodeSpecRecord] = Field(default_factory=list)
    tph_item_code_supps: list[TPHItemCodeSuppRecord] = Field(default_factory=list)
    tph_sample_plans: list[TPHSamplePlanRecord] = Field(default_factory=list)
    tph_sample_plan_entries: list[TPHSamplePlanEntryRecord] = Field(default_factory=list)
    customers: list[CustomerRecord] = Field(default_factory=list)
    t_sites: list[TSiteRecord] = Field(default_factory=list)
    t_plants: list[TPlantRecord] = Field(default_factory=list)
    t_suites: list[TSuiteRecord] = Field(default_factory=list)
    process_units: list[ProcessUnitRecord] = Field(default_factory=list)
    proc_sched_parents: list[ProcSchedParentRecord] = Field(default_factory=list)
    process_schedules: list[ProcessScheduleRecord] = Field(default_factory=list)
    lists: list[ListRecord] = Field(default_factory=list)
    list_entries: list[ListEntryRecord] = Field(default_factory=list)
    vendors: list[VendorRecord] = Field(default_factory=list)
    suppliers: list[SupplierRecord] = Field(default_factory=list)
    instruments: list[InstrumentRecord] = Field(default_factory=list)
    lims_users: list[LimsUserRecord] = Field(default_factory=list)
    versions: list[VersionRecord] = Field(default_factory=list)

    # Quality control
    validation_errors: list[dict[str, Any]] = Field(default_factory=list)
    audit_log: list[dict[str, Any]] = Field(default_factory=list)
    overall_confidence: float = 0.0

    def record_count(self) -> dict[str, int]:
        return {key: len(getattr(self, key)) for key in SHEET_KEYS}


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
