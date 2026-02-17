"""
excel_generator.py - Generate a multi-sheet LIMS Load Sheet Excel file.

Uses openpyxl with custom styling:
  - Header row: blue background, white bold text
  - Low-confidence cells: yellow highlight
  - Validation error cells: red highlight
  - Auto column widths
  - Freeze top row
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from models.schemas import ExtractionResult

logger = logging.getLogger(__name__)

# ── Colour constants ──────────────────────────────────────────────────────────
_HEADER_FILL = PatternFill("solid", fgColor="1F5C9E")
_HEADER_FONT = Font(bold=True, color="FFFFFF", name="Calibri", size=11)
_LOW_CONF_FILL = PatternFill("solid", fgColor="FFEB9C")   # yellow
_ERROR_FILL = PatternFill("solid", fgColor="FFC7CE")      # red
_BORDER_SIDE = Side(style="thin", color="CCCCCC")
_CELL_BORDER = Border(
    left=_BORDER_SIDE, right=_BORDER_SIDE,
    top=_BORDER_SIDE, bottom=_BORDER_SIDE,
)
_NORMAL_FONT = Font(name="Calibri", size=10)


# ── Sheet definitions ─────────────────────────────────────────────────────────

SHEET_SPECS: list[dict[str, Any]] = [
    {
        "name": "Analysis",
        "data_attr": "analysis",
        "columns": ["Name", "Group Name", "Reported Name", "Description", "Common Name", "Analysis Type"],
        "field_map": ["name", "group_name", "reported_name", "description", "common_name", "analysis_type"],
    },
    {
        "name": "Component",
        "data_attr": "components",
        "columns": ["Analysis", "Name", "Num Replicates", "Order Number", "Result Type", "Units", "Minimum", "Maximum"],
        "field_map": ["analysis", "name", "num_replicates", "order_number", "result_type", "units", "minimum", "maximum"],
    },
    {
        "name": "Units",
        "data_attr": "units",
        "columns": ["Unit Code", "Description", "Display String", "Group Name"],
        "field_map": ["unit_code", "description", "display_string", "group_name"],
    },
    {
        "name": "Product",
        "data_attr": "products",
        "columns": ["Name", "Description", "Group Name"],
        "field_map": ["name", "description", "group_name"],
    },
    {
        "name": "Product Grade",
        "data_attr": "product_grades",
        "columns": ["Description", "Continue Checking", "Test List", "Always Check", "C STP NO", "C Spec No"],
        "field_map": ["description", "continue_checking", "test_list", "always_check", "c_stp_no", "c_spec_no"],
    },
    {
        "name": "Prod Grade Stage",
        "data_attr": "prod_grade_stages",
        "columns": [
            "Product", "Sampling Point", "Grade", "Stage", "Heading", "Analysis",
            "Order Number", "Description", "Spec Type", "Num Reps", "Reported Name",
            "Required", "Test Location", "Required Volume", "File Name",
        ],
        "field_map": [
            "product", "sampling_point", "grade", "stage", "heading", "analysis",
            "order_number", "description", "spec_type", "num_reps", "reported_name",
            "required", "test_location", "required_volume", "file_name",
        ],
    },
    {
        "name": "Product Spec",
        "data_attr": "product_specs",
        "columns": [
            "Product", "Sampling Point", "Spec Type", "Grade", "Stage", "Analysis",
            "Reported Name", "Description", "Heading", "Component", "Units",
            "Round", "Place", "Spec Rule", "Min Value", "Max Value", "Text Value",
            "Class", "File Name", "Show On Certificate", "C Stock", "Rule Type",
        ],
        "field_map": [
            "product", "sampling_point", "spec_type", "grade", "stage", "analysis",
            "reported_name", "description", "heading", "component", "units",
            "round", "place", "spec_rule", "min_value", "max_value", "text_value",
            "class_", "file_name", "show_on_certificate", "c_stock", "rule_type",
        ],
    },
    {
        "name": "T PH ITEM CODE",
        "data_attr": "tph_item_codes",
        "columns": ["Name", "Description", "Group Name", "Display As", "Sample Plan", "Site"],
        "field_map": ["name", "description", "group_name", "display_as", "sample_plan", "site"],
    },
    {
        "name": "T PH ITEM CODE Spec",
        "data_attr": "tph_item_code_specs",
        "columns": ["T PH Item Code", "Spec Code", "Product Spec", "Spec Class", "Order Number", "Grade"],
        "field_map": ["t_ph_item_code", "spec_code", "product_spec", "spec_class", "order_number", "grade"],
    },
    {
        "name": "T PH ITEM CODE SUPP",
        "data_attr": "tph_item_code_supps",
        "columns": [
            "T PH Item Code", "Supplier", "Active", "Status 1", "Status 2",
            "Order Number", "Retest Interval", "Expiry Interval",
            "Full Test Frequency", "Lots To Go", "Date Last Tested",
        ],
        "field_map": [
            "t_ph_item_code", "supplier", "active", "status_1", "status_2",
            "order_number", "retest_interval", "expiry_interval",
            "full_test_frequency", "lots_to_go", "date_last_tested",
        ],
    },
    {
        "name": "T PH SAMPLE PLAN",
        "data_attr": "tph_sample_plans",
        "columns": ["Name", "Description", "Group Name"],
        "field_map": ["name", "description", "group_name"],
    },
    {
        "name": "T PH SAMPLE PLAN Entry",
        "data_attr": "tph_sample_plan_entries",
        "columns": [
            "T PH Sample Plan", "Entry Code", "Description", "Order Number",
            "Spec Type", "Stage", "Algorithm", "Log Sample", "Create Inventory",
            "Retained Sample", "Stability", "Initial Status", "Num Samples",
            "Quantity", "Units", "Sampling Point", "Test Location",
        ],
        "field_map": [
            "t_ph_sample_plan", "entry_code", "description", "order_number",
            "spec_type", "stage", "algorithm", "log_sample", "create_inventory",
            "retained_sample", "stability", "initial_status", "num_samples",
            "quantity", "units", "sampling_point", "test_location",
        ],
    },
]


class ExcelGenerator:
    """Generate a styled, multi-sheet LIMS Load Sheet Excel workbook."""

    def generate(
        self,
        result: ExtractionResult,
        output_path: str | Path,
        validation_issues: list[dict] | None = None,
    ) -> Path:
        """
        Write the ExtractionResult to an Excel workbook.

        Args:
            result: The validated extraction result.
            output_path: Target .xlsx file path.
            validation_issues: Optional list of validation issue dicts for cell highlighting.

        Returns:
            Path to the written file.
        """
        output_path = Path(output_path)
        wb = openpyxl.Workbook()

        # Remove default empty sheet
        wb.remove(wb.active)

        issue_index = self._build_issue_index(validation_issues or [])

        sheets_written = []
        for spec in SHEET_SPECS:
            rows = getattr(result, spec["data_attr"], [])
            if rows:
                self._write_sheet(wb, spec, rows, issue_index)
                sheets_written.append(spec["name"])
            else:
                # Write empty sheet with headers so template is intact
                self._write_sheet(wb, spec, [], issue_index)

        # Add a Summary sheet
        self._write_summary(wb, result, sheets_written)

        wb.save(str(output_path))
        logger.info("Excel workbook saved to %s (%d sheets)", output_path, len(wb.sheetnames))
        return output_path

    # ── Private helpers ───────────────────────────────────────────────────

    def _write_sheet(
        self,
        wb: openpyxl.Workbook,
        spec: dict[str, Any],
        records: list[Any],
        issue_index: dict[str, set[tuple[int, str]]],
    ) -> None:
        """Write one sheet to the workbook."""
        ws = wb.create_sheet(title=spec["name"])

        # Header row
        for col_idx, col_name in enumerate(spec["columns"], start=1):
            cell = ws.cell(row=1, column=col_idx, value=col_name)
            cell.fill = _HEADER_FILL
            cell.font = _HEADER_FONT
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = _CELL_BORDER

        ws.row_dimensions[1].height = 30
        ws.freeze_panes = "A2"

        # Data rows
        sheet_issues = issue_index.get(spec["name"], set())

        for row_idx, record in enumerate(records, start=2):
            is_low_conf = getattr(record, "confidence", 1.0) < 0.6

            for col_idx, field in enumerate(spec["field_map"], start=1):
                value = getattr(record, field, None)
                cell = ws.cell(row=row_idx, column=col_idx, value=value)
                cell.font = _NORMAL_FONT
                cell.border = _CELL_BORDER
                cell.alignment = Alignment(vertical="center", wrap_text=True)

                col_name = spec["columns"][col_idx - 1]
                if (row_idx - 2, col_name) in sheet_issues:
                    cell.fill = _ERROR_FILL
                elif is_low_conf:
                    cell.fill = _LOW_CONF_FILL

        # Auto-fit column widths
        self._auto_width(ws, spec["columns"])

    def _write_summary(
        self,
        wb: openpyxl.Workbook,
        result: ExtractionResult,
        sheets_written: list[str],
    ) -> None:
        ws = wb.create_sheet(title="Summary", index=0)

        rows = [
            ("LIMS Load Sheet", ""),
            ("Document Name", result.document_name),
            ("Document Type", result.document_type),
            ("Job ID", result.job_id),
            ("Overall Confidence", f"{result.overall_confidence:.1%}"),
            ("", ""),
            ("Sheet", "Records"),
        ]
        counts = result.record_count()
        for sheet_name in sheets_written:
            attr = next(
                (s["data_attr"] for s in SHEET_SPECS if s["name"] == sheet_name), None
            )
            rows.append((sheet_name, counts.get(attr, 0) if attr else 0))

        for r_idx, (label, value) in enumerate(rows, start=1):
            ws.cell(row=r_idx, column=1, value=label).font = Font(bold=True, name="Calibri")
            ws.cell(row=r_idx, column=2, value=value).font = Font(name="Calibri")

        ws.column_dimensions["A"].width = 30
        ws.column_dimensions["B"].width = 40

    @staticmethod
    def _auto_width(ws: Any, columns: list[str]) -> None:
        """Set column widths based on header + data cell lengths."""
        for col_idx, header in enumerate(columns, start=1):
            col_letter = get_column_letter(col_idx)
            max_width = len(header) + 4
            for row in ws.iter_rows(min_col=col_idx, max_col=col_idx):
                for cell in row:
                    if cell.value:
                        max_width = max(max_width, min(len(str(cell.value)) + 2, 50))
            ws.column_dimensions[col_letter].width = max_width

    @staticmethod
    def _build_issue_index(
        issues: list[dict],
    ) -> dict[str, set[tuple[int, str]]]:
        """Build {sheet_name: {(row_index, field_name)}} for fast cell lookup."""
        index: dict[str, set] = {}
        for issue in issues:
            sheet = issue.get("sheet", "")
            row = issue.get("row_index", -1)
            field = issue.get("field", "")
            if sheet:
                index.setdefault(sheet, set()).add((row, field))
        return index
