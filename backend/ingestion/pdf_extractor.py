"""
pdf_extractor.py - Extract text and tables from digital PDF files.

Uses pdfplumber for digital PDFs (vector text) and falls back to
OCRProcessor for image-only pages.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pdfplumber

from .ocr_processor import OCRProcessor

logger = logging.getLogger(__name__)


@dataclass
class PageContent:
    page_number: int
    raw_text: str
    tables: list[list[list[str | None]]]   # list of tables; each table is rows×cols
    is_ocr: bool = False


class PDFExtractor:
    """
    Extract structured content from digital or scanned PDF files.

    Strategy:
      1. Try pdfplumber for each page (fast, accurate for digital PDFs).
      2. If a page has < MIN_TEXT_CHARS characters, treat it as an image
         page and run OCR via OCRProcessor.
    """

    MIN_TEXT_CHARS = 20   # threshold below which we consider a page image-only

    def __init__(self, ocr_enabled: bool = True, ocr_language: str = "eng") -> None:
        self.ocr_enabled = ocr_enabled
        self._ocr = OCRProcessor(language=ocr_language) if ocr_enabled else None

    # ── Public API ────────────────────────────────────────────────────────────

    def extract(self, file_path: str | Path) -> list[PageContent]:
        """Extract all pages from a PDF.  Returns a list of PageContent objects."""
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"PDF not found: {file_path}")

        pages: list[PageContent] = []

        with pdfplumber.open(str(file_path)) as pdf:
            logger.info("Opened PDF %s (%d pages)", file_path.name, len(pdf.pages))

            for page in pdf.pages:
                page_num = page.page_number
                text = page.extract_text() or ""
                tables = self._extract_tables(page)

                # Check if this is likely an image-only page
                if len(text.strip()) < self.MIN_TEXT_CHARS and self.ocr_enabled and self._ocr:
                    logger.debug("Page %d has little text; attempting OCR", page_num)
                    ocr_text = self._ocr.extract_page_from_pdf(str(file_path), page_num - 1)
                    if ocr_text.strip():
                        text = ocr_text
                        pages.append(PageContent(
                            page_number=page_num,
                            raw_text=text,
                            tables=tables,
                            is_ocr=True,
                        ))
                        continue

                pages.append(PageContent(
                    page_number=page_num,
                    raw_text=text,
                    tables=tables,
                    is_ocr=False,
                ))

        logger.info("Extracted %d pages from %s", len(pages), file_path.name)
        return pages

    def extract_full_text(self, file_path: str | Path) -> str:
        """Convenience method – returns all pages concatenated as plain text."""
        pages = self.extract(file_path)
        return "\n\n---PAGE BREAK---\n\n".join(
            f"[Page {p.page_number}]\n{p.raw_text}" for p in pages
        )

    def extract_tables_only(self, file_path: str | Path) -> list[dict[str, Any]]:
        """Return every table found across all pages with page context."""
        pages = self.extract(file_path)
        result = []
        for page in pages:
            for idx, table in enumerate(page.tables):
                result.append({
                    "page": page.page_number,
                    "table_index": idx,
                    "rows": table,
                    "row_count": len(table),
                    "col_count": max((len(r) for r in table), default=0),
                })
        return result

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _extract_tables(page: Any) -> list[list[list[str | None]]]:
        """Extract tables from a pdfplumber page, converting cells to strings."""
        tables = []
        try:
            raw_tables = page.extract_tables()
            for raw in (raw_tables or []):
                # Normalise: ensure every cell is str or None
                cleaned = [
                    [str(cell).strip() if cell is not None else None for cell in row]
                    for row in raw
                ]
                tables.append(cleaned)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Table extraction failed on page %s: %s", page.page_number, exc)
        return tables
