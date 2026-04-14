/**
 * lims.ts - TypeScript interfaces for all 30 LIMS Load Sheet types.
 * Mirrors the Python Pydantic schemas in backend/models/schemas.py.
 */

// ── Job / confidence types ──────────────────────────────────────────────────

export type JobStatus = 'pending' | 'extracting' | 'mapping' | 'validating' | 'complete' | 'failed';
export type ConfidenceLevel = 'high' | 'medium' | 'low';

export interface Annotated {
  confidence: number;
  confidence_level?: ConfidenceLevel;
  review_notes?: string;
  source_text?: string;
}

// ── 1. ANALYSIS_TYPES ───────────────────────────────────────────────────────

export interface AnalysisTypeRecord extends Annotated {
  name: string;
  description?: string;
  group_name?: string;
}

// ── 2. COMMON_NAME ──────────────────────────────────────────────────────────

export interface CommonNameRecord extends Annotated {
  name: string;
  description?: string;
  group_name?: string;
}

// ── 3. ANALYSIS ─────────────────────────────────────────────────────────────

export interface AnalysisRecord extends Annotated {
  name: string;
  version?: string;
  group_name?: string;
  active?: string;
  reported_name?: string;
  common_name?: string;
  analysis_type?: string;
  description?: string;
}

// ── 4. COMPONENT ────────────────────────────────────────────────────────────

export interface ComponentRecord extends Annotated {
  analysis: string;
  name: string;
  num_replicates?: number;
  version?: string;
  order_number?: number;
  result_type?: string;
  units?: string;
  minimum?: number;
  maximum?: number;
}

// ── 5. UNITS ────────────────────────────────────────────────────────────────

export interface UnitRecord extends Annotated {
  unit_code: string;
  description?: string;
  display_string?: string;
  group_name?: string;
}

// ── 6. PRODUCT ──────────────────────────────────────────────────────────────

export interface ProductRecord extends Annotated {
  product: string;
  version?: string;
  sampling_point?: string;
  grade?: string;
  order_number?: number;
  description?: string;
  continue_checking?: string;
  test_list?: string;
  always_check?: string;
  t_ph_same_lot?: string;
  t_ph_status1?: string;
  t_ph_status2?: string;
  t_ph_recert?: string;
  t_usp_secondary?: string;
  test_location?: string;
  reqd_volume?: string;
  aliquot_group?: string;
  c_spec_variation?: string;
  c_test_group?: string;
}

// ── 7. T_PH_GRADE ──────────────────────────────────────────────────────────

export interface TPHGradeRecord extends Annotated {
  name: string;
  description?: string;
  group_name?: string;
  active?: string;
  code?: string;
}

// ── 8. SAMPLING_POINT ──────────────────────────────────────────────────────

export interface SamplingPointRecord extends Annotated {
  name: string;
  description?: string;
  group_name?: string;
}

// ── 9. PRODUCT_GRADE ───────────────────────────────────────────────────────

export interface ProductGradeRecord extends Annotated {
  product?: string;
  version?: string;
  grade?: string;
  order_number?: number;
  description?: string;
  continue_checking?: string;
  test_list?: string;
  always_check?: string;
}

// ── 10. PROD_GRADE_STAGE ───────────────────────────────────────────────────

export interface ProdGradeStageRecord extends Annotated {
  product: string;
  version?: string;
  sampling_point?: string;
  grade?: string;
  stage?: string;
  analysis?: string;
  order_number?: number;
  description?: string;
  spec_type?: string;
  num_reps?: number;
  partial?: string;
  ext_link?: string;
  reported_name?: string;
  variation?: string;
  required?: string;
}

// ── 11. PRODUCT_SPEC ───────────────────────────────────────────────────────

export interface ProductSpecRecord extends Annotated {
  product: string;
  version?: string;
  sampling_point?: string;
  grade?: string;
  stage?: string;
  analysis?: string;
  component?: string;
  units?: string;
  round?: number;
  rule_type?: string;
  spec_rule?: string;
  min_value?: number;
  max_value?: number;
  text_value?: string;
  class_?: string;
  required?: string;
}

// ── 12. T_PH_ITEM_CODE ────────────────────────────────────────────────────

export interface TPHItemCodeRecord extends Annotated {
  t_ph_item_code: string;
  supplier?: string;
  active?: string;
  status1?: string;
  status2?: string;
  order_number?: number;
  retest_interval?: number;
  expiry_interval?: number;
  full_test_freq?: number;
  lots_to_go?: number;
  date_last_tested?: string;
}

// ── 13. T_PH_ITEM_CODE_SPEC ──────────────────────────────────────────────

export interface TPHItemCodeSpecRecord extends Annotated {
  spec_code?: string;
  t_ph_item_code: string;
  product_spec?: string;
  spec_class?: string;
  order_number?: number;
  grade?: string;
  common_grade?: string;
}

// ── 14. T_PH_ITEM_CODE_SUPP ─────────────────────────────────────────────

export interface TPHItemCodeSuppRecord extends Annotated {
  t_ph_item_code: string;
  supplier?: string;
  active?: string;
  status1?: string;
  status2?: string;
  order_number?: number;
}

// ── 15. T_PH_SAMPLE_PLAN ───────────────────────────────────────────────

export interface TPHSamplePlanRecord extends Annotated {
  name: string;
  version?: string;
  active?: string;
  description?: string;
  group_name?: string;
}

// ── 16. T_PH_SAMPLE_PLAN_EN ────────────────────────────────────────────

export interface TPHSamplePlanEntryRecord extends Annotated {
  t_ph_sample_plan: string;
  entry_code?: string;
  version?: string;
  description?: string;
  order_number?: number;
  spec_type?: string;
  spec_status?: string;
  t_ph_sample_type?: string;
  log_sample?: string;
  create_inventory?: string;
  retained_sample?: string;
  stability?: string;
  initial_status?: string;
  indic_samples?: number;
  quantity?: number;
  units?: string;
  c_reanalysis_qty?: string;
  c_stm_quantity?: string;
}

// ── 17. CUSTOMER ───────────────────────────────────────────────────────

export interface CustomerRecord extends Annotated {
  name: string;
  group_name?: string;
  description?: string;
  company_name?: string;
  address1?: string;
  address2?: string;
  address3?: string;
  address4?: string;
  address5?: string;
  address6?: string;
  fax_num?: string;
  phone_num?: string;
  contact?: string;
  email_addr?: string;
}

// ── 18. T_SITE ─────────────────────────────────────────────────────────

export interface TSiteRecord extends Annotated {
  name: string;
  description?: string;
  group_name?: string;
  parent_site?: string;
}

// ── 19. T_PLANT ────────────────────────────────────────────────────────

export interface TPlantRecord extends Annotated {
  name: string;
  description?: string;
  group_name?: string;
  site?: string;
  personnel_smp_type?: string;
  personnel_stage?: string;
  personnel_spec_type?: string;
}

// ── 20. T_SUITE ────────────────────────────────────────────────────────

export interface TSuiteRecord extends Annotated {
  name: string;
  description?: string;
  group_name?: string;
  plant?: string;
  visual_workflow?: string;
  corrective_action?: string;
  restrict_collection?: string;
}

// ── 21. PROCESS_UNIT ───────────────────────────────────────────────────

export interface ProcessUnitRecord extends Annotated {
  name: string;
  description?: string;
  group_name?: string;
  product_grade?: string;
  sample_template?: string;
  running?: string;
  phase?: string;
  default_phase?: string;
  t_alternate_grade?: string;
  t_corrective_action?: string;
  t_suite?: string;
}

// ── 22. PROC_SCHED_PARENT ──────────────────────────────────────────────

export interface ProcSchedParentRecord extends Annotated {
  name: string;
  first_day_of_week?: string;
  treat_holidays_as?: string;
  workstation?: string;
  running?: string;
  description?: string;
  group_name?: string;
  active_flag?: string;
  version?: string;
  t_site?: string;
}

// ── 23. PROCESS_SCHEDULE ───────────────────────────────────────────────

export interface ProcessScheduleRecord extends Annotated {
  schedule_number?: string;
  login_offset?: string;
  schd_collect_time?: string;
  unit?: string;
  sampling_point?: string;
  test_list?: string;
  analyses?: string;
  description?: string;
  schedule_name?: string;
  order_number?: number;
  running?: string;
  phase?: string;
  version?: string;
  spec_type?: string;
  stage?: string;
}

// ── 24. LIST ───────────────────────────────────────────────────────────

export interface ListRecord extends Annotated {
  list_name: string;
  name: string;
  value?: string;
  order_number?: number;
}

// ── 25. LIST_ENTRY ─────────────────────────────────────────────────────

export interface ListEntryRecord extends Annotated {
  name: string;
  group_name?: string;
  description?: string;
}

// ── 26. VENDOR ─────────────────────────────────────────────────────────

export interface VendorRecord extends Annotated {
  name: string;
  description?: string;
  contact?: string;
  company_name?: string;
  address1?: string;
  address2?: string;
  address3?: string;
  address4?: string;
  address5?: string;
  address6?: string;
  fax_num?: string;
  phone_num?: string;
  group_name?: string;
}

// ── 27. SUPPLIER ───────────────────────────────────────────────────────

export interface SupplierRecord extends Annotated {
  name: string;
  description?: string;
  contact?: string;
  company_name?: string;
  address1?: string;
  address2?: string;
  address3?: string;
  address4?: string;
  address5?: string;
  address6?: string;
  fax_num?: string;
  phone_num?: string;
  group_name?: string;
}

// ── 28. INSTRUMENTS ────────────────────────────────────────────────────

export interface InstrumentRecord extends Annotated {
  name: string;
  group_name?: string;
  description?: string;
  inst_group?: string;
  vendor?: string;
  on_line?: string;
  serial_no?: string;
  pm_date?: string;
  pm_intv?: string;
  calib_date?: string;
  calib_intv?: string;
  model_no?: string;
}

// ── 29. LIMS_USERS ─────────────────────────────────────────────────────

export interface LimsUserRecord extends Annotated {
  user_name: string;
  full_name?: string;
  phone?: string;
  group_name?: string;
  description?: string;
  email_addr?: string;
  is_role?: string;
  uses_roles?: string;
  language_prefix?: string;
  t_site?: string;
  location_lab?: string;
}

// ── 30. VERSIONS ───────────────────────────────────────────────────────

export interface VersionRecord extends Annotated {
  table_name?: string;
  version?: string;
  description?: string;
}

// ── Validation ─────────────────────────────────────────────────────────

export interface ValidationIssue {
  sheet: string;
  row_index?: number;
  field: string;
  message: string;
  severity: 'error' | 'warning';
}

// ── Extraction Result ──────────────────────────────────────────────────

export interface ExtractionResult {
  job_id: string;
  document_type: string;
  document_name: string;
  status: JobStatus;
  progress: number;
  message: string;

  // All 30 sheets
  analysis_types: AnalysisTypeRecord[];
  common_names: CommonNameRecord[];
  analysis: AnalysisRecord[];
  components: ComponentRecord[];
  units: UnitRecord[];
  products: ProductRecord[];
  tph_grades: TPHGradeRecord[];
  sampling_points: SamplingPointRecord[];
  product_grades: ProductGradeRecord[];
  prod_grade_stages: ProdGradeStageRecord[];
  product_specs: ProductSpecRecord[];
  tph_item_codes: TPHItemCodeRecord[];
  tph_item_code_specs: TPHItemCodeSpecRecord[];
  tph_item_code_supps: TPHItemCodeSuppRecord[];
  tph_sample_plans: TPHSamplePlanRecord[];
  tph_sample_plan_entries: TPHSamplePlanEntryRecord[];
  customers: CustomerRecord[];
  t_sites: TSiteRecord[];
  t_plants: TPlantRecord[];
  t_suites: TSuiteRecord[];
  process_units: ProcessUnitRecord[];
  proc_sched_parents: ProcSchedParentRecord[];
  process_schedules: ProcessScheduleRecord[];
  lists: ListRecord[];
  list_entries: ListEntryRecord[];
  vendors: VendorRecord[];
  suppliers: SupplierRecord[];
  instruments: InstrumentRecord[];
  lims_users: LimsUserRecord[];
  versions: VersionRecord[];

  validation_errors: ValidationIssue[];
  audit_log: Record<string, unknown>[];
  overall_confidence: number;
}

// ── Job types ──────────────────────────────────────────────────────────

export interface JobSummary {
  id: string;
  filename: string;
  original_filename: string;
  status: JobStatus;
  document_type: string;
  created_at: string;
  updated_at?: string;
  error_message?: string;
  download_count?: number;
  reprocess_count?: number;
}

export interface JobDetail extends JobSummary {
  result?: ExtractionResult;
}

// ── Audit log ──────────────────────────────────────────────────────────

export interface AuditLogEntry {
  id: number
  job_id: string
  sheet_name: string
  field_name: string
  old_value: string | null
  new_value: string | null
  context_text: string | null
  change_source: 'manual' | 'ai_refine'
  changed_at: string
}

// ── UI types ───────────────────────────────────────────────────────────

export interface ColumnDef {
  field: string;
  headerName: string;
  width?: number;
  editable?: boolean;
}

export interface SheetDef {
  dataKey: string;
  name: string;
  columns: ColumnDef[];
}
