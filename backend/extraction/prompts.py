"""
prompts.py - LLM prompt templates for LIMS document extraction.

Each function returns a formatted prompt string ready for the LLM.
Prompts use few-shot examples and explicit JSON schemas to maximise
structured output reliability.
"""

from __future__ import annotations


# ── Document classifier prompt ─────────────────────────────────────────────

CLASSIFIER_SYSTEM = """You are an expert LIMS (Laboratory Information Management System) document analyst.
Your task is to classify the type of laboratory document provided."""

CLASSIFIER_USER = """Analyse this document excerpt and determine its type.

Document text (first 3000 characters):
{text}

Respond with a JSON object ONLY (no markdown, no explanation):
{{
  "document_type": "STP" | "PTP" | "SPEC" | "METHOD" | "SOP" | "OTHER",
  "confidence": 0.0-1.0,
  "reasoning": "brief explanation",
  "detected_sections": ["list", "of", "detected", "section", "headings"],
  "product_hints": ["any product names found"],
  "analysis_hints": ["any analysis/test method names found"]
}}"""


# ── Analysis extraction prompt ─────────────────────────────────────────────

ANALYSIS_SYSTEM = """You are an expert LIMS data extraction specialist.
Extract analytical test information from laboratory documents and return structured JSON.

LIMS Definitions:
- Analysis: A test method or analytical procedure (e.g., "Moisture Content", "pH Determination")
- Group Name: The category grouping (e.g., "Physical", "Chemical", "Microbiological")
- Analysis Type: The classification (e.g., "Chemical", "Physical", "Micro", "Organoleptic")
- Reported Name: The name shown on certificates/reports (may differ from the code name)
"""

ANALYSIS_USER = """Extract all Analysis records from this document section.

Document text:
{text}

Return a JSON array of analysis records. Each record must follow this schema:
{{
  "name": "UNIQUE_CODE_NO_SPACES",
  "group_name": "Physical|Chemical|Microbiological|Other",
  "reported_name": "Human readable test name",
  "description": "Full description if available",
  "common_name": "Common abbreviation or alias",
  "analysis_type": "Chemical|Physical|Micro|Organoleptic|Calculated",
  "confidence": 0.0-1.0,
  "review_notes": "Flag any ambiguous mappings"
}}

Rules:
- Name must be a unique identifier (uppercase, no spaces, e.g. MOISTURE, PH_VALUE)
- Include ALL tests/analyses mentioned, even if data is incomplete
- Set confidence < 0.7 if you are uncertain about a mapping
- Return [] if no analysis data is found

Return ONLY the JSON array, no other text."""


# ── Component extraction prompt ────────────────────────────────────────────

COMPONENT_SYSTEM = """You are an expert LIMS data extraction specialist.
Extract component/parameter information from laboratory documents.

LIMS Definitions:
- Component: A specific measured parameter within an Analysis (e.g., "Moisture %", "pH Value")
- Result Type: How the result is reported (Numeric, Text, Boolean, Pass/Fail)
- Units: The measurement unit (link to Units sheet)
- Num Replicates: How many repeat measurements are performed
"""

COMPONENT_USER = """Extract all Component records from this document section.

Document text:
{text}

Known analyses from this document (use these for the 'analysis' foreign key):
{known_analyses}

Return a JSON array. Each record:
{{
  "analysis": "PARENT_ANALYSIS_NAME",
  "name": "COMPONENT_NAME",
  "num_replicates": 1,
  "order_number": 1,
  "result_type": "Numeric|Text|Boolean|Pass/Fail",
  "units": "unit_code",
  "minimum": null,
  "maximum": null,
  "confidence": 0.0-1.0,
  "review_notes": "notes"
}}

Rules:
- analysis must match a name from the known_analyses list
- If you can't determine the parent analysis, set confidence to 0.5
- minimum/maximum should be numeric or null
- Return [] if no component data found

Return ONLY the JSON array."""


# ── Units extraction prompt ────────────────────────────────────────────────

UNITS_USER = """Extract all measurement units from this document section.

Document text:
{text}

Return a JSON array. Each record:
{{
  "unit_code": "UPPERCASE_CODE",
  "description": "Full description",
  "display_string": "Display format e.g. %, mg/kg, °C",
  "group_name": "Mass|Volume|Concentration|Temperature|Other",
  "confidence": 0.0-1.0
}}

Examples of unit codes: PCT (%), MGKG (mg/kg), CELSIUS (°C), PPM (ppm)
Return ONLY the JSON array."""


# ── Product extraction prompt ──────────────────────────────────────────────

PRODUCT_USER = """Extract all Product records from this document.

Document text:
{text}

Return a JSON array. Each record:
{{
  "name": "PRODUCT_CODE_OR_NAME",
  "description": "Full product description",
  "group_name": "Product category/group",
  "confidence": 0.0-1.0,
  "review_notes": "notes"
}}

Return ONLY the JSON array."""


# ── Product Spec extraction prompt ─────────────────────────────────────────

PRODUCT_SPEC_SYSTEM = """You are an expert LIMS data extraction specialist.
Extract product specification data (acceptance limits) from laboratory documents.

LIMS Definitions:
- Spec Type: Type of specification (Release, Shelf Life, Regulatory)
- Grade: Quality grade (e.g., Premium, Standard, Reject)
- Stage: Process stage (e.g., Raw Material, In Process, Finished Product)
- Spec Rule: How the limit is applied (Between, LessThan, GreaterThan, EqualTo)
- Min/Max Value: Numeric acceptance limits
- Text Value: For Pass/Fail or categorical results
"""

PRODUCT_SPEC_USER = """Extract all Product Specification records from this document.

Document text:
{text}

Known products: {known_products}
Known analyses: {known_analyses}
Known components: {known_components}

Return a JSON array. Each record:
{{
  "product": "PRODUCT_NAME",
  "sampling_point": "Receiving|In-Process|Final|Stability",
  "spec_type": "Release|Shelf-Life|Regulatory|Internal",
  "grade": "Premium|Standard|Reject|null",
  "stage": "Raw Material|In Process|Finished Product",
  "analysis": "ANALYSIS_NAME",
  "reported_name": "Name on report",
  "description": "Description",
  "heading": "Section heading",
  "component": "COMPONENT_NAME",
  "units": "unit_code",
  "round": null,
  "place": null,
  "spec_rule": "Between|LessThan|GreaterThan|EqualTo|Text",
  "min_value": null,
  "max_value": null,
  "text_value": null,
  "show_on_certificate": "Y|N",
  "rule_type": "Pass/Fail|Limit|Target",
  "confidence": 0.0-1.0,
  "review_notes": "notes"
}}

Return ONLY the JSON array."""


# ── Sample Plan extraction prompt ─────────────────────────────────────────

SAMPLE_PLAN_USER = """Extract all Sample Plan records from this document.

Document text:
{text}

Return a JSON array of sample plans:
{{
  "name": "PLAN_CODE",
  "description": "Plan description",
  "group_name": "Group",
  "confidence": 0.0-1.0
}}

And a separate JSON array for Sample Plan Entries (return as object with two keys):
{{
  "sample_plans": [...],
  "sample_plan_entries": [
    {{
      "t_ph_sample_plan": "PLAN_CODE",
      "entry_code": "ENTRY_CODE",
      "description": "Entry description",
      "order_number": 1,
      "spec_type": "Release",
      "stage": "Receiving",
      "algorithm": null,
      "log_sample": "Y",
      "create_inventory": "Y",
      "retained_sample": "N",
      "stability": "N",
      "initial_status": "Pending",
      "num_samples": 1,
      "quantity": null,
      "units": null,
      "sampling_point": null,
      "test_location": null,
      "confidence": 0.0-1.0
    }}
  ]
}}"""


# ── Prod Grade Stage extraction ────────────────────────────────────────────

PROD_GRADE_STAGE_USER = """Extract all Product Grade Stage records from this document.
These define what tests are performed at each stage for each product grade.

Document text:
{text}

Known products: {known_products}
Known analyses: {known_analyses}

Return a JSON array. Each record:
{{
  "product": "PRODUCT_NAME",
  "sampling_point": "Receiving|In-Process|Final",
  "grade": "Grade name",
  "stage": "Stage name",
  "heading": "Section heading",
  "analysis": "ANALYSIS_NAME",
  "order_number": 1,
  "description": "Description",
  "spec_type": "Release",
  "num_reps": 1,
  "reported_name": "Reported name",
  "required": "Y|N",
  "test_location": "Lab name",
  "required_volume": null,
  "file_name": null,
  "confidence": 0.0-1.0,
  "review_notes": "notes"
}}

Return ONLY the JSON array."""


# ── T PH Item Code extraction ──────────────────────────────────────────────

TPH_ITEM_CODE_USER = """Extract all T PH Item Code records (pharmaceutical item/product codes).

Document text:
{text}

Return an object with two arrays:
{{
  "item_codes": [
    {{
      "name": "ITEM_CODE",
      "description": "Description",
      "group_name": "Group",
      "display_as": "Display name",
      "sample_plan": "PLAN_CODE",
      "site": "Site name",
      "confidence": 0.0-1.0
    }}
  ],
  "item_code_specs": [
    {{
      "t_ph_item_code": "ITEM_CODE",
      "spec_code": "SPEC_CODE",
      "product_spec": "PRODUCT_SPEC",
      "spec_class": "Class",
      "order_number": 1,
      "grade": "Grade",
      "confidence": 0.0-1.0
    }}
  ],
  "item_code_supps": [
    {{
      "t_ph_item_code": "ITEM_CODE",
      "supplier": "Supplier name",
      "active": "Y",
      "status_1": null,
      "status_2": null,
      "order_number": 1,
      "retest_interval": null,
      "expiry_interval": null,
      "full_test_frequency": null,
      "lots_to_go": null,
      "date_last_tested": null,
      "confidence": 0.0-1.0
    }}
  ]
}}"""
