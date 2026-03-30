"""Document ingestion package - PDF, DOCX, and OCR extraction."""
from .pdf_extractor import PDFExtractor
from .docx_extractor import DOCXExtractor
from .ocr_processor import OCRProcessor
from .dispatcher import ingest_document, ExtractedDocument

__all__ = ["PDFExtractor", "DOCXExtractor", "OCRProcessor", "ingest_document", "ExtractedDocument"]
