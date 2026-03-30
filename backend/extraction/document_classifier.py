"""
document_classifier.py - Classify the type of LIMS document using the LLM.

Supported document types:
  STP  – Standard Testing Procedure
  PTP  – Product Testing Procedure
  SPEC – Product Specification
  METHOD – Analytical Method
  SOP  – Standard Operating Procedure
  OTHER – Cannot be determined
"""

from __future__ import annotations

import json
import logging
from enum import Enum

from langchain_core.messages import HumanMessage, SystemMessage

from .prompts import CLASSIFIER_SYSTEM, CLASSIFIER_USER
from .llm_factory import get_llm

logger = logging.getLogger(__name__)


class DocumentType(str, Enum):
    STP = "STP"
    PTP = "PTP"
    SPEC = "SPEC"
    METHOD = "METHOD"
    SOP = "SOP"
    OTHER = "OTHER"


class ClassificationResult:
    def __init__(
        self,
        document_type: DocumentType,
        confidence: float,
        reasoning: str,
        detected_sections: list[str],
        product_hints: list[str],
        analysis_hints: list[str],
    ) -> None:
        self.document_type = document_type
        self.confidence = confidence
        self.reasoning = reasoning
        self.detected_sections = detected_sections
        self.product_hints = product_hints
        self.analysis_hints = analysis_hints


class DocumentClassifier:
    """Use an LLM to determine the LIMS document type."""

    def __init__(self) -> None:
        self._llm = get_llm()

    def classify(self, text: str) -> ClassificationResult:
        """Classify the document from the first 3000 characters of text."""
        excerpt = text[:3000]
        prompt = CLASSIFIER_USER.format(text=excerpt)

        logger.info("Classifying document type...")
        try:
            messages = [
                SystemMessage(content=CLASSIFIER_SYSTEM),
                HumanMessage(content=prompt),
            ]
            response = self._llm.invoke(messages)
            raw = response.content.strip()

            # Strip markdown code fences if present
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            raw = raw.strip()

            data = json.loads(raw)
            doc_type_str = data.get("document_type", "OTHER").upper()
            try:
                doc_type = DocumentType(doc_type_str)
            except ValueError:
                doc_type = DocumentType.OTHER

            return ClassificationResult(
                document_type=doc_type,
                confidence=float(data.get("confidence", 0.5)),
                reasoning=data.get("reasoning", ""),
                detected_sections=data.get("detected_sections", []),
                product_hints=data.get("product_hints", []),
                analysis_hints=data.get("analysis_hints", []),
            )

        except (json.JSONDecodeError, KeyError) as exc:
            logger.warning("Classification parse error: %s – defaulting to OTHER", exc)
            return ClassificationResult(
                document_type=DocumentType.OTHER,
                confidence=0.3,
                reasoning=f"Parse error: {exc}",
                detected_sections=[],
                product_hints=[],
                analysis_hints=[],
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("Classification LLM error: %s", exc)
            return ClassificationResult(
                document_type=DocumentType.OTHER,
                confidence=0.0,
                reasoning=f"LLM error: {exc}",
                detected_sections=[],
                product_hints=[],
                analysis_hints=[],
            )
