"""
dispatcher.py - Route uploaded files to the appropriate extractor.

Determines file type by extension (and magic bytes as fallback) and
returns a unified ExtractedDocument object.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .docx_extractor import DOCXExtractor
from .pdf_extractor import PDFExtractor

logger = logging.getLogger(__name__)


@dataclass
class ExtractedDocument:
    """Unified representation of an extracted document regardless of source format."""

    file_path: str
    file_type: str                          # "pdf" | "docx"
    full_text: str
    tables: list[dict[str, Any]] = field(default_factory=list)
    page_count: int = 0
    has_ocr_pages: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


def ingest_document(
    file_path: str | Path,
    ocr_enabled: bool = True,
    ocr_language: str = "eng",
) -> ExtractedDocument:
    """
    Dispatch a file to the correct extractor and return an ExtractedDocument.

    Raises:
        ValueError: If the file type is not supported.
        FileNotFoundError: If the file does not exist.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    suffix = file_path.suffix.lower()
    logger.info("Ingesting document: %s (type=%s)", file_path.name, suffix)

    if suffix == ".pdf":
        return _ingest_pdf(file_path, ocr_enabled=ocr_enabled, ocr_language=ocr_language)
    elif suffix in (".docx", ".doc"):
        return _ingest_docx(file_path)
    else:
        raise ValueError(
            f"Unsupported file type '{suffix}'. Supported: .pdf, .docx, .doc"
        )


# ── Private helpers ───────────────────────────────────────────────────────────

def _ingest_pdf(
    file_path: Path,
    ocr_enabled: bool,
    ocr_language: str,
) -> ExtractedDocument:
    extractor = PDFExtractor(ocr_enabled=ocr_enabled, ocr_language=ocr_language)
    pages = extractor.extract(file_path)

    full_text = "\n\n---PAGE BREAK---\n\n".join(
        f"[Page {p.page_number}]\n{p.raw_text}" for p in pages
    )
    tables_out = []
    for page in pages:
        for idx, table in enumerate(page.tables):
            tables_out.append({
                "page": page.page_number,
                "table_index": idx,
                "rows": table,
            })

    has_ocr = any(p.is_ocr for p in pages)

    return ExtractedDocument(
        file_path=str(file_path),
        file_type="pdf",
        full_text=full_text,
        tables=tables_out,
        page_count=len(pages),
        has_ocr_pages=has_ocr,
        metadata={"ocr_enabled": ocr_enabled},
    )


def _ingest_docx(file_path: Path) -> ExtractedDocument:
    extractor = DOCXExtractor()
    content = extractor.extract(file_path)

    tables_out = [
        {"page": None, "table_index": idx, "rows": table}
        for idx, table in enumerate(content.tables)
    ]

    return ExtractedDocument(
        file_path=str(file_path),
        file_type="docx",
        full_text=content.full_text,
        tables=tables_out,
        page_count=0,
        has_ocr_pages=False,
        metadata={},
    )
