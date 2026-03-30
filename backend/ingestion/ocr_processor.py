"""
ocr_processor.py - Tesseract OCR wrapper for scanned PDF pages and images.

Converts PDF pages to high-resolution images via pdf2image, then extracts
text with pytesseract.  Requires Tesseract installed on the OS.
"""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import pytesseract
    from PIL import Image
    from pdf2image import convert_from_path
    _OCR_AVAILABLE = True
except ImportError:
    _OCR_AVAILABLE = False
    logger.warning("pytesseract / pdf2image not available – OCR disabled")


class OCRProcessor:
    """Perform OCR on scanned images or PDF pages."""

    DPI = 300          # Render DPI – higher = better quality, slower
    PSMODE = 3         # Tesseract page segmentation mode (3 = full auto)

    def __init__(self, language: str = "eng", tesseract_cmd: str | None = None) -> None:
        if not _OCR_AVAILABLE:
            raise RuntimeError(
                "OCR dependencies not installed. "
                "Run: pip install pytesseract pdf2image Pillow"
            )
        self.language = language
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    # ── Public API ────────────────────────────────────────────────────────────

    def extract_page_from_pdf(self, pdf_path: str, page_index: int) -> str:
        """
        OCR a single zero-based page index from a PDF.

        Returns extracted text or empty string on failure.
        """
        try:
            images = convert_from_path(
                pdf_path,
                dpi=self.DPI,
                first_page=page_index + 1,
                last_page=page_index + 1,
            )
            if not images:
                return ""
            return self._ocr_image(images[0])
        except Exception as exc:  # noqa: BLE001
            logger.error("OCR failed for page %d of %s: %s", page_index, pdf_path, exc)
            return ""

    def extract_all_pages(self, pdf_path: str) -> list[str]:
        """OCR every page of a PDF.  Returns list of text per page."""
        try:
            images = convert_from_path(pdf_path, dpi=self.DPI)
            return [self._ocr_image(img) for img in images]
        except Exception as exc:  # noqa: BLE001
            logger.error("Full-PDF OCR failed for %s: %s", pdf_path, exc)
            return []

    def extract_image(self, image_path: str | Path) -> str:
        """OCR a standalone image file."""
        try:
            img = Image.open(str(image_path))
            return self._ocr_image(img)
        except Exception as exc:  # noqa: BLE001
            logger.error("Image OCR failed for %s: %s", image_path, exc)
            return ""

    # ── Private helpers ───────────────────────────────────────────────────────

    def _ocr_image(self, image: "Image.Image") -> str:  # type: ignore[name-defined]
        """Run Tesseract on a PIL Image and return the text."""
        config = f"--psm {self.PSMODE}"
        text = pytesseract.image_to_string(image, lang=self.language, config=config)
        return text.strip()
