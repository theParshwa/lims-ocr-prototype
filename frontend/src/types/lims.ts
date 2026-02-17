// ============================================================
// LIMS OCR - TypeScript type definitions
// Mirrors the Python Pydantic schemas exactly.
// ============================================================

export type JobStatus =
  | 'pending'
  | 'extracting'
  | 'mapping'
  | 'validating'
  | 'complete'
  | 'failed'

export type ConfidenceLevel = 'high' | 'medium' | 'low'

// ── Per-record annotation fields (stripped before Excel export) ──────────────
export interface Annotated {
  confidence: number        // 0.0 – 1.0
  confidence_level?: ConfidenceLevel
  review_notes?: string
  source_text?: string
}

// ── Analysis Sheet ────────────────────────────────────────────────────────────
export interface AnalysisRecord extends Annotated {
  name: string
  group_name?: string
  reported_name?: string
  description?: string
  common_name?: string
  analysis_type?: string
}

// ── Component Sheet ───────────────────────────────────────────────────────────
export interface ComponentRecord extends Annotated {
  analysis: string
  name: string
  num_replicates?: number
  order_number?: number
  result_type?: string
  units?: string
  minimum?: number
  maximum?: number
}

// ── Units Sheet ───────────────────────────────────────────────────────────────
export interface UnitRecord extends Annotated {
  unit_code: string
  description?: string
  display_string?: string
  group_name?: string
}

// ── Product Sheet ─────────────────────────────────────────────────────────────
export interface ProductRecord extends Annotated {
  name: string
  description?: string
  group_name?: string
}

// ── Product Grade Sheet ───────────────────────────────────────────────────────
export interface ProductGradeRecord extends Annotated {
  description: string
  continue_checking?: string
  test_list?: string
  always_check?: string
  c_stp_no?: string
  c_spec_no?: string
}

// ── Prod Grade Stage Sheet ────────────────────────────────────────────────────
export interface ProdGradeStageRecord extends Annotated {
  product: string
  sampling_point?: string
  grade?: string
  stage?: string
  heading?: string
  analysis?: string
  order_number?: number
  description?: string
  spec_type?: string
  num_reps?: number
  reported_name?: string
  required?: string
  test_location?: string
  required_volume?: number
  file_name?: string
}

// ── Product Spec Sheet ────────────────────────────────────────────────────────
export interface ProductSpecRecord extends Annotated {
  product: string
  sampling_point?: string
  spec_type?: string
  grade?: string
  stage?: string
  analysis?: string
  reported_name?: string
  description?: string
  heading?: string
  component?: string
  units?: string
  round?: number
  place?: number
  spec_rule?: string
  min_value?: number
  max_value?: number
  text_value?: string
  class_?: string
  file_name?: string
  show_on_certificate?: string
  c_stock?: string
  rule_type?: string
}

// ── T PH Item Code ────────────────────────────────────────────────────────────
export interface TPHItemCodeRecord extends Annotated {
  name: string
  description?: string
  group_name?: string
  display_as?: string
  sample_plan?: string
  site?: string
}

export interface TPHItemCodeSpecRecord extends Annotated {
  t_ph_item_code: string
  spec_code?: string
  product_spec?: string
  spec_class?: string
  order_number?: number
  grade?: string
}

export interface TPHItemCodeSuppRecord extends Annotated {
  t_ph_item_code: string
  supplier?: string
  active?: string
  status_1?: string
  status_2?: string
  order_number?: number
  retest_interval?: number
  expiry_interval?: number
  full_test_frequency?: number
  lots_to_go?: number
  date_last_tested?: string
}

// ── T PH Sample Plan ──────────────────────────────────────────────────────────
export interface TPHSamplePlanRecord extends Annotated {
  name: string
  description?: string
  group_name?: string
}

export interface TPHSamplePlanEntryRecord extends Annotated {
  t_ph_sample_plan: string
  entry_code?: string
  description?: string
  order_number?: number
  spec_type?: string
  stage?: string
  algorithm?: string
  log_sample?: string
  create_inventory?: string
  retained_sample?: string
  stability?: string
  initial_status?: string
  num_samples?: number
  quantity?: number
  units?: string
  sampling_point?: string
  test_location?: string
}

// ── Validation Issue ──────────────────────────────────────────────────────────
export interface ValidationIssue {
  sheet: string
  row_index?: number
  field: string
  message: string
  severity: 'error' | 'warning'
}

// ── Extraction Result ─────────────────────────────────────────────────────────
export interface ExtractionResult {
  job_id: string
  document_type: string
  document_name: string
  status: JobStatus
  progress: number
  message: string

  analysis: AnalysisRecord[]
  components: ComponentRecord[]
  units: UnitRecord[]
  products: ProductRecord[]
  product_grades: ProductGradeRecord[]
  prod_grade_stages: ProdGradeStageRecord[]
  product_specs: ProductSpecRecord[]
  tph_item_codes: TPHItemCodeRecord[]
  tph_item_code_specs: TPHItemCodeSpecRecord[]
  tph_item_code_supps: TPHItemCodeSuppRecord[]
  tph_sample_plans: TPHSamplePlanRecord[]
  tph_sample_plan_entries: TPHSamplePlanEntryRecord[]

  validation_errors: ValidationIssue[]
  audit_log: Record<string, unknown>[]
  overall_confidence: number
}

// ── Job Summary ───────────────────────────────────────────────────────────────
export interface JobSummary {
  job_id: string
  filename: string
  status: JobStatus
  document_type: string
  created_at?: string
  updated_at?: string
  output_path?: string
}

export interface JobDetail extends JobSummary {
  result?: ExtractionResult
  error_message?: string
}

// ── Sheet definitions for UI ──────────────────────────────────────────────────
export interface SheetDef {
  name: string
  dataKey: keyof ExtractionResult
  columns: ColumnDef[]
}

export interface ColumnDef {
  field: string
  headerName: string
  type?: 'text' | 'number' | 'boolean'
  editable?: boolean
  width?: number
}
