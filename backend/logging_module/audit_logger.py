"""
audit_logger.py - Structured audit logging for all processing decisions.

Emits JSON log entries that record:
  - Every stage of the pipeline
  - LLM inputs/outputs (truncated)
  - Mapping decisions with rationale
  - Validation results
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog

# ── Configure structlog ───────────────────────────────────────────────────────

def configure_logging(log_level: str = "INFO", log_file: str | None = None) -> None:
    """Initialise structlog for the application."""
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.ExceptionRenderer(),
        structlog.processors.JSONRenderer(),
    ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(
            file=open(log_file, "a", encoding="utf-8") if log_file else sys.stdout
        ),
    )


class AuditLogger:
    """High-level structured logger for LIMS processing pipeline events."""

    def __init__(self, job_id: str) -> None:
        self._job_id = job_id
        self._log = structlog.get_logger().bind(job_id=job_id)
        self._entries: list[dict[str, Any]] = []

    # ── Logging helpers ───────────────────────────────────────────────────

    def pipeline_start(self, file_name: str, file_type: str) -> None:
        entry = self._entry("pipeline_start", file_name=file_name, file_type=file_type)
        self._log.info("Pipeline started", **entry)

    def stage_complete(self, stage: str, duration_ms: float, details: dict | None = None) -> None:
        entry = self._entry("stage_complete", stage=stage, duration_ms=duration_ms, **(details or {}))
        self._log.info("Stage complete", **entry)

    def document_classified(self, doc_type: str, confidence: float, reasoning: str) -> None:
        entry = self._entry(
            "document_classified",
            document_type=doc_type,
            confidence=confidence,
            reasoning=reasoning,
        )
        self._log.info("Document classified", **entry)

    def entity_extracted(self, entity_type: str, count: int, avg_confidence: float) -> None:
        entry = self._entry(
            "entity_extracted",
            entity_type=entity_type,
            count=count,
            avg_confidence=avg_confidence,
        )
        self._log.info("Entities extracted", **entry)

    def mapping_decision(self, field: str, value: str, rule: str, confidence: float) -> None:
        entry = self._entry(
            "mapping_decision",
            field=field,
            value=value,
            rule=rule,
            confidence=confidence,
        )
        self._log.debug("Mapping decision", **entry)

    def validation_issue(self, sheet: str, field: str, message: str, severity: str) -> None:
        entry = self._entry(
            "validation_issue",
            sheet=sheet,
            field=field,
            message=message,
            severity=severity,
        )
        self._log.warning("Validation issue", **entry)

    def pipeline_complete(self, record_counts: dict[str, int], overall_confidence: float) -> None:
        entry = self._entry(
            "pipeline_complete",
            record_counts=record_counts,
            overall_confidence=overall_confidence,
        )
        self._log.info("Pipeline complete", **entry)

    def error(self, stage: str, error: str) -> None:
        entry = self._entry("error", stage=stage, error=error)
        self._log.error("Pipeline error", **entry)

    def get_entries(self) -> list[dict[str, Any]]:
        return self._entries.copy()

    # ── Private ───────────────────────────────────────────────────────────

    def _entry(self, event: str, **kwargs: Any) -> dict[str, Any]:
        entry = {
            "event": event,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **kwargs,
        }
        self._entries.append(entry)
        return entry
