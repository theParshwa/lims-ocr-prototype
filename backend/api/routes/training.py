"""
training.py - REST endpoints for managing training examples.

POST   /api/training          — upload a completed Load Sheet Excel
GET    /api/training          — list all training examples
DELETE /api/training/{id}     — remove a training example
"""

from __future__ import annotations

import logging
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db
from config import settings
from training.training_manager import TrainingManager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/training", tags=["training"])

_manager = TrainingManager()

# Directory for training Excel files
TRAINING_DIR = settings.upload_dir.parent / "training"
TRAINING_DIR.mkdir(parents=True, exist_ok=True)


@router.post("", summary="Upload a training example (completed Load Sheet Excel)")
async def upload_training_example(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: str = Form(""),
    session: AsyncSession = Depends(get_db),
):
    # Validate file type
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".xlsx", ".xls"}:
        raise HTTPException(status_code=400, detail="Only Excel files (.xlsx / .xls) are accepted.")

    # Read and check size
    MAX_BYTES = settings.max_upload_size_mb * 1024 * 1024
    content = await file.read()
    await file.close()
    if len(content) > MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({len(content) // 1024 // 1024} MB). Max: {settings.max_upload_size_mb} MB",
        )

    # Save file
    unique_name = f"{uuid.uuid4().hex}{suffix}"
    dest = TRAINING_DIR / unique_name
    dest.write_bytes(content)

    # Parse + persist
    try:
        example = await _manager.add_example(
            session,
            name=name.strip(),
            file_path=dest,
            description=description.strip() or None,
        )
    except Exception as exc:
        dest.unlink(missing_ok=True)
        logger.error("Failed to parse training example: %s", exc)
        raise HTTPException(status_code=422, detail=f"Could not parse Excel file: {exc}") from exc

    # Auto-embed into RAG vector store
    try:
        from rag.retriever import store_embedding
        from training.excel_parser import build_training_prompt_context
        parsed = example.get_parsed() or {}
        embed_text = build_training_prompt_context([example.to_dict()])
        await store_embedding(
            session,
            source_type="training",
            source_id=str(example.id),
            text=embed_text[:4000],
            metadata={"name": example.name, "description": example.description or ""},
        )
        logger.info("Embedded training example '%s' into RAG store", example.name)
    except Exception as exc:
        logger.warning("RAG embedding failed for training example: %s", exc)

    return example.to_dict()


@router.get("", summary="List all training examples")
async def list_training_examples(session: AsyncSession = Depends(get_db)):
    examples = await _manager.list_examples(session)
    return [ex.to_dict() for ex in examples]


@router.delete("/{example_id}", summary="Delete a training example")
async def delete_training_example(
    example_id: int,
    session: AsyncSession = Depends(get_db),
):
    example = await _manager.get_example(session, example_id)
    if not example:
        raise HTTPException(status_code=404, detail="Training example not found.")

    # Remove file from disk
    try:
        Path(example.file_path).unlink(missing_ok=True)
    except Exception:
        pass

    deleted = await _manager.delete_example(session, example_id)
    return {"deleted": deleted, "id": example_id}
