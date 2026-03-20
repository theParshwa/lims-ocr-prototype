"""
training_manager.py - CRUD operations for training examples stored in SQLite.

Training examples are completed Load Sheet Excel files uploaded by the user.
They are parsed, stored, and later injected as few-shot context into LLM prompts.
"""

from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from models.lims_models import TrainingExample
from training.excel_parser import parse_training_excel

logger = logging.getLogger(__name__)


class TrainingManager:
    """Manages training example storage and retrieval."""

    async def add_example(
        self,
        session: AsyncSession,
        name: str,
        file_path: str | Path,
        description: str | None = None,
    ) -> TrainingExample:
        """Parse an uploaded Excel file and persist it as a training example."""
        parsed = parse_training_excel(file_path)
        example = TrainingExample(
            name=name,
            description=description,
            file_path=str(file_path),
        )
        example.set_parsed(parsed)
        session.add(example)
        await session.commit()
        await session.refresh(example)
        logger.info("Added training example '%s' (id=%s)", name, example.id)
        return example

    async def list_examples(self, session: AsyncSession) -> list[TrainingExample]:
        result = await session.execute(
            select(TrainingExample).order_by(TrainingExample.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_example(
        self, session: AsyncSession, example_id: int
    ) -> TrainingExample | None:
        result = await session.execute(
            select(TrainingExample).where(TrainingExample.id == example_id)
        )
        return result.scalar_one_or_none()

    async def delete_example(
        self, session: AsyncSession, example_id: int
    ) -> bool:
        result = await session.execute(
            delete(TrainingExample).where(TrainingExample.id == example_id)
        )
        await session.commit()
        return result.rowcount > 0

    async def get_all_parsed(self, session: AsyncSession) -> list[dict]:
        """Return parsed content for ALL examples — used for prompt injection."""
        examples = await self.list_examples(session)
        return [ex.to_dict() for ex in examples]
