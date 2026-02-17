/**
 * sheetDefs.ts - Defines column layouts for each LIMS Load Sheet tab.
 *
 * Used by the AG Grid data preview to configure columns per sheet.
 */

import type { SheetDef } from '@/types/lims'

export const SHEET_DEFS: SheetDef[] = [
  {
    name: 'Analysis',
    dataKey: 'analysis',
    columns: [
      { field: 'name',          headerName: 'Name',          width: 160 },
      { field: 'group_name',    headerName: 'Group Name',    width: 140 },
      { field: 'reported_name', headerName: 'Reported Name', width: 160 },
      { field: 'description',   headerName: 'Description',   width: 250 },
      { field: 'common_name',   headerName: 'Common Name',   width: 140 },
      { field: 'analysis_type', headerName: 'Analysis Type', width: 140 },
      { field: 'confidence',    headerName: 'Confidence',    width: 110, type: 'number' },
      { field: 'review_notes',  headerName: 'Review Notes',  width: 200 },
    ],
  },
  {
    name: 'Component',
    dataKey: 'components',
    columns: [
      { field: 'analysis',       headerName: 'Analysis',       width: 160 },
      { field: 'name',           headerName: 'Name',           width: 160 },
      { field: 'num_replicates', headerName: 'Num Replicates', width: 130, type: 'number' },
      { field: 'order_number',   headerName: 'Order Number',   width: 120, type: 'number' },
      { field: 'result_type',    headerName: 'Result Type',    width: 120 },
      { field: 'units',          headerName: 'Units',          width: 100 },
      { field: 'minimum',        headerName: 'Minimum',        width: 100, type: 'number' },
      { field: 'maximum',        headerName: 'Maximum',        width: 100, type: 'number' },
      { field: 'confidence',     headerName: 'Confidence',     width: 110, type: 'number' },
    ],
  },
  {
    name: 'Units',
    dataKey: 'units',
    columns: [
      { field: 'unit_code',      headerName: 'Unit Code',     width: 120 },
      { field: 'description',    headerName: 'Description',   width: 200 },
      { field: 'display_string', headerName: 'Display String',width: 140 },
      { field: 'group_name',     headerName: 'Group Name',    width: 140 },
    ],
  },
  {
    name: 'Product',
    dataKey: 'products',
    columns: [
      { field: 'name',        headerName: 'Name',        width: 180 },
      { field: 'description', headerName: 'Description', width: 280 },
      { field: 'group_name',  headerName: 'Group Name',  width: 160 },
    ],
  },
  {
    name: 'Product Grade',
    dataKey: 'product_grades',
    columns: [
      { field: 'description',       headerName: 'Description',       width: 200 },
      { field: 'continue_checking', headerName: 'Continue Checking', width: 150 },
      { field: 'test_list',         headerName: 'Test List',         width: 160 },
      { field: 'always_check',      headerName: 'Always Check',      width: 130 },
      { field: 'c_stp_no',          headerName: 'C STP NO',          width: 120 },
      { field: 'c_spec_no',         headerName: 'C Spec No',         width: 120 },
    ],
  },
  {
    name: 'Prod Grade Stage',
    dataKey: 'prod_grade_stages',
    columns: [
      { field: 'product',          headerName: 'Product',          width: 150 },
      { field: 'sampling_point',   headerName: 'Sampling Point',   width: 140 },
      { field: 'grade',            headerName: 'Grade',            width: 100 },
      { field: 'stage',            headerName: 'Stage',            width: 120 },
      { field: 'heading',          headerName: 'Heading',          width: 150 },
      { field: 'analysis',         headerName: 'Analysis',         width: 150 },
      { field: 'order_number',     headerName: 'Order Number',     width: 120, type: 'number' },
      { field: 'description',      headerName: 'Description',      width: 200 },
      { field: 'spec_type',        headerName: 'Spec Type',        width: 120 },
      { field: 'num_reps',         headerName: 'Num Reps',         width: 100, type: 'number' },
      { field: 'reported_name',    headerName: 'Reported Name',    width: 150 },
      { field: 'required',         headerName: 'Required',         width: 100 },
      { field: 'test_location',    headerName: 'Test Location',    width: 140 },
      { field: 'required_volume',  headerName: 'Required Volume',  width: 140, type: 'number' },
    ],
  },
  {
    name: 'Product Spec',
    dataKey: 'product_specs',
    columns: [
      { field: 'product',             headerName: 'Product',              width: 140 },
      { field: 'sampling_point',      headerName: 'Sampling Point',       width: 140 },
      { field: 'spec_type',           headerName: 'Spec Type',            width: 120 },
      { field: 'grade',               headerName: 'Grade',                width: 100 },
      { field: 'stage',               headerName: 'Stage',                width: 120 },
      { field: 'analysis',            headerName: 'Analysis',             width: 150 },
      { field: 'reported_name',       headerName: 'Reported Name',        width: 150 },
      { field: 'component',           headerName: 'Component',            width: 150 },
      { field: 'units',               headerName: 'Units',                width: 80 },
      { field: 'spec_rule',           headerName: 'Spec Rule',            width: 120 },
      { field: 'min_value',           headerName: 'Min Value',            width: 100, type: 'number' },
      { field: 'max_value',           headerName: 'Max Value',            width: 100, type: 'number' },
      { field: 'text_value',          headerName: 'Text Value',           width: 120 },
      { field: 'show_on_certificate', headerName: 'Show On Certificate',  width: 160 },
      { field: 'confidence',          headerName: 'Confidence',           width: 110, type: 'number' },
      { field: 'review_notes',        headerName: 'Review Notes',         width: 200 },
    ],
  },
  {
    name: 'T PH ITEM CODE',
    dataKey: 'tph_item_codes',
    columns: [
      { field: 'name',        headerName: 'Name',        width: 160 },
      { field: 'description', headerName: 'Description', width: 240 },
      { field: 'group_name',  headerName: 'Group Name',  width: 140 },
      { field: 'display_as',  headerName: 'Display As',  width: 140 },
      { field: 'sample_plan', headerName: 'Sample Plan', width: 140 },
      { field: 'site',        headerName: 'Site',        width: 120 },
    ],
  },
  {
    name: 'T PH ITEM CODE Spec',
    dataKey: 'tph_item_code_specs',
    columns: [
      { field: 't_ph_item_code', headerName: 'T PH Item Code', width: 150 },
      { field: 'spec_code',      headerName: 'Spec Code',      width: 120 },
      { field: 'product_spec',   headerName: 'Product Spec',   width: 150 },
      { field: 'spec_class',     headerName: 'Spec Class',     width: 120 },
      { field: 'order_number',   headerName: 'Order Number',   width: 120, type: 'number' },
      { field: 'grade',          headerName: 'Grade',          width: 100 },
    ],
  },
  {
    name: 'T PH ITEM CODE SUPP',
    dataKey: 'tph_item_code_supps',
    columns: [
      { field: 't_ph_item_code',      headerName: 'T PH Item Code',       width: 150 },
      { field: 'supplier',            headerName: 'Supplier',             width: 160 },
      { field: 'active',              headerName: 'Active',               width: 80 },
      { field: 'retest_interval',     headerName: 'Retest Interval',      width: 130, type: 'number' },
      { field: 'expiry_interval',     headerName: 'Expiry Interval',      width: 130, type: 'number' },
      { field: 'full_test_frequency', headerName: 'Full Test Frequency',  width: 160, type: 'number' },
    ],
  },
  {
    name: 'T PH SAMPLE PLAN',
    dataKey: 'tph_sample_plans',
    columns: [
      { field: 'name',        headerName: 'Name',        width: 160 },
      { field: 'description', headerName: 'Description', width: 280 },
      { field: 'group_name',  headerName: 'Group Name',  width: 140 },
    ],
  },
  {
    name: 'T PH SAMPLE PLAN Entry',
    dataKey: 'tph_sample_plan_entries',
    columns: [
      { field: 't_ph_sample_plan', headerName: 'T PH Sample Plan', width: 160 },
      { field: 'entry_code',       headerName: 'Entry Code',       width: 120 },
      { field: 'description',      headerName: 'Description',      width: 200 },
      { field: 'order_number',     headerName: 'Order Number',     width: 120, type: 'number' },
      { field: 'spec_type',        headerName: 'Spec Type',        width: 120 },
      { field: 'stage',            headerName: 'Stage',            width: 120 },
      { field: 'num_samples',      headerName: 'Num Samples',      width: 120, type: 'number' },
      { field: 'sampling_point',   headerName: 'Sampling Point',   width: 140 },
      { field: 'test_location',    headerName: 'Test Location',    width: 140 },
    ],
  },
]
