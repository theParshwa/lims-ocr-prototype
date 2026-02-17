"""
lims_models.py - SQLAlchemy ORM models for persisting job history.

Uses async SQLite via aiosqlite for lightweight, no-dependency storage.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class LIMSJob(Base):
    """Persisted record for every uploaded document / processing job."""

    __tablename__ = "lims_jobs"

    id = Column(String(36), primary_key=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(1024), nullable=False)
    status = Column(String(32), default="pending", nullable=False)
    document_type = Column(String(64), default="unknown")
    created_at = Column(DateTime, default=_utcnow, nullable=False)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)
    error_message = Column(Text, nullable=True)
    output_path = Column(String(1024), nullable=True)

    # Full extraction result stored as JSON blob
    result_json = Column(Text, nullable=True)

    def set_result(self, result: dict) -> None:
        self.result_json = json.dumps(result)

    def get_result(self) -> dict | None:
        if self.result_json:
            return json.loads(self.result_json)
        return None


class TrainingExample(Base):
    """A completed Load Sheet uploaded by the user to train the AI."""

    __tablename__ = "training_examples"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    file_path = Column(String(1024), nullable=False)
    parsed_content = Column(Text, nullable=True)  # JSON from excel_parser
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    def set_parsed(self, content: dict) -> None:
        self.parsed_content = json.dumps(content)

    def get_parsed(self) -> dict | None:
        if self.parsed_content:
            return json.loads(self.parsed_content)
        return None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "parsed_content": self.get_parsed(),
        }


class LIMSLoadSheet(Base):
    """Represents a generated Excel load sheet file."""

    __tablename__ = "lims_load_sheets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(36), nullable=False, index=True)
    file_path = Column(String(1024), nullable=False)
    created_at = Column(DateTime, default=_utcnow, nullable=False)
    sheet_counts = Column(Text, nullable=True)  # JSON dict of sheet→row counts

    def set_counts(self, counts: dict) -> None:
        self.sheet_counts = json.dumps(counts)

    def get_counts(self) -> dict:
        if self.sheet_counts:
            return json.loads(self.sheet_counts)
        return {}
