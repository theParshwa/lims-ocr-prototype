"""
pipeline.py - Orchestrates the full document extraction pipeline.

Pipeline stages:
  1. Ingest document (PDF/DOCX)
  2. Classify document type
  3. Extract LIMS entities via LLM
  4. Return structured ExtractionResult
"""

from __future__ import annotations

import logging
from typing import Callable

from ingestion.dispatcher import ExtractedDocument, ingest_document
from models.schemas import ExtractionResult, JobStatus
from .document_classifier import DocumentClassifier
from .entity_extractor import EntityExtractor

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[int, str], None]


class ExtractionPipeline:
    """
    Runs the full extraction pipeline for a single document.

    Usage:
        pipeline = ExtractionPipeline()
        result = pipeline.run(file_path, job_id, on_progress=callback)
    """

    def __init__(
        self,
        ocr_enabled: bool = True,
        ocr_language: str = "eng",
        chunk_size: int = 4000,
        chunk_overlap: int = 400,
    ) -> None:
        self._classifier = DocumentClassifier()
        self._extractor = EntityExtractor(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        self._ocr_enabled = ocr_enabled
        self._ocr_language = ocr_language

    def run(
        self,
        file_path: str,
        job_id: str,
        document_name: str = "",
        on_progress: ProgressCallback | None = None,
        training_context: str = "",
        document_type_hint: str | None = None,
    ) -> ExtractionResult:
        """
        Execute the full pipeline and return an ExtractionResult.

        on_progress: optional callable(percent: int, message: str)
        """
        result = ExtractionResult(job_id=job_id, document_name=document_name)
        audit: list[dict] = []

        def progress(pct: int, msg: str) -> None:
            result.progress = pct
            result.message = msg
            audit.append({"progress": pct, "message": msg})
            logger.info("[%d%%] %s", pct, msg)
            if on_progress:
                on_progress(pct, msg)

        try:
            # Stage 1: Ingest
            result.status = JobStatus.EXTRACTING
            progress(5, "Ingesting document...")
            doc: ExtractedDocument = ingest_document(
                file_path,
                ocr_enabled=self._ocr_enabled,
                ocr_language=self._ocr_language,
            )
            audit.append({
                "stage": "ingest",
                "file_type": doc.file_type,
                "page_count": doc.page_count,
                "has_ocr": doc.has_ocr_pages,
                "text_length": len(doc.full_text),
                "table_count": len(doc.tables),
            })

            # Stage 2: Classify (or apply user hint)
            progress(15, "Classifying document type...")
            classification = self._classifier.classify(doc.full_text)
            if document_type_hint:
                result.document_type = document_type_hint.upper()
                logger.info("Document type overridden by user hint: %s", result.document_type)
            else:
                result.document_type = classification.document_type.value
            audit.append({
                "stage": "classification",
                "document_type": classification.document_type.value,
                "confidence": classification.confidence,
                "reasoning": classification.reasoning,
            })
            progress(20, f"Detected document type: {result.document_type}")

            # Stage 3: Extract entities
            progress(25, "Extracting LIMS entities (this may take a moment)...")
            tables_text = self._tables_to_text(doc.tables)
            entities = self._extractor.extract_all(doc.full_text, tables_text, training_context)
            result.status = JobStatus.MAPPING

            # Stage 4: Populate result — all 30 sheets
            progress(80, "Mapping extracted entities to LIMS schema...")
            from models.schemas import SHEET_KEYS
            for key in SHEET_KEYS:
                setattr(result, key, entities.get(key, []))

            # Stage 5: Compute overall confidence
            result.overall_confidence = self._compute_confidence(result)
            result.audit_log = audit

            result.status = JobStatus.VALIDATING
            progress(90, "Running validation checks...")
            # Validation is handled by the validation module (called from the API layer)

            result.status = JobStatus.COMPLETE
            progress(100, "Extraction complete.")

            counts = result.record_count()
            logger.info(
                "Extraction complete for job %s | records: %s", job_id, counts
            )

        except Exception as exc:  # noqa: BLE001
            result.status = JobStatus.FAILED
            result.message = str(exc)
            audit.append({"stage": "error", "error": str(exc)})
            result.audit_log = audit
            logger.exception("Pipeline failed for job %s: %s", job_id, exc)

        return result

    # ── Helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _tables_to_text(tables: list[dict]) -> str:
        """Serialise extracted tables to plain text for LLM consumption."""
        lines = []
        for t in tables:
            page_str = f"Page {t['page']}" if t.get("page") else "DOCX"
            lines.append(f"[Table from {page_str}]")
            for row in t.get("rows", []):
                cells = [str(c) if c is not None else "" for c in row]
                lines.append(" | ".join(cells))
            lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _compute_confidence(result: ExtractionResult) -> float:
        """Average confidence across all extracted records."""
        all_records = (
            result.analysis
            + result.components
            + result.units
            + result.products
            + result.product_specs
        )
        if not all_records:
            return 0.0
        return round(sum(r.confidence for r in all_records) / len(all_records), 3)
