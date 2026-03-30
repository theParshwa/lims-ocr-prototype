"""
rag.py - Endpoints for inspecting the RAG knowledge base.

GET  /api/rag/stats        — total embedding counts by type
GET  /api/rag/corrections  — paginated list of captured corrections
DELETE /api/rag/corrections/{id} — remove a single correction + its embedding
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db
from models.lims_models import CorrectionExample, RAGEmbedding

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/rag", tags=["rag"])


@router.get("/stats", summary="RAG knowledge base statistics")
async def rag_stats(session: AsyncSession = Depends(get_db)):
    """Return total embedding counts broken down by source_type."""
    # Total embeddings
    total_result = await session.execute(select(func.count(RAGEmbedding.id)))
    total = total_result.scalar() or 0

    # Per-type counts
    type_result = await session.execute(
        select(RAGEmbedding.source_type, func.count(RAGEmbedding.id))
        .group_by(RAGEmbedding.source_type)
    )
    by_type = {row[0]: row[1] for row in type_result.all()}

    # Correction count (from CorrectionExample table — ground truth)
    corr_result = await session.execute(select(func.count(CorrectionExample.id)))
    correction_count = corr_result.scalar() or 0

    return {
        "total_embeddings": total,
        "training_embeddings": by_type.get("training", 0),
        "correction_embeddings": by_type.get("correction", 0),
        "correction_examples": correction_count,
    }


@router.get("/corrections", summary="List captured user corrections")
async def list_corrections(
    session: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    sheet_name: str | None = Query(None),
    document_type: str | None = Query(None),
):
    """Return captured correction examples, newest first."""
    stmt = select(CorrectionExample).order_by(CorrectionExample.created_at.desc())
    if sheet_name:
        stmt = stmt.where(CorrectionExample.sheet_name == sheet_name)
    if document_type:
        stmt = stmt.where(CorrectionExample.document_type == document_type)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await session.execute(count_stmt)
    total = total_result.scalar() or 0

    stmt = stmt.offset(offset).limit(limit)
    result = await session.execute(stmt)
    items = result.scalars().all()

    return {
        "total": total,
        "corrections": [c.to_dict() for c in items],
    }


@router.delete("/corrections/{correction_id}", summary="Delete a correction example")
async def delete_correction(
    correction_id: int,
    session: AsyncSession = Depends(get_db),
):
    """Remove a correction and its associated embedding."""
    correction = await session.get(CorrectionExample, correction_id)
    if not correction:
        raise HTTPException(status_code=404, detail="Correction not found.")

    # Remove associated embedding if present
    emb_result = await session.execute(
        select(RAGEmbedding).where(
            RAGEmbedding.source_type == "correction",
            RAGEmbedding.source_id == str(correction_id),
        )
    )
    for emb in emb_result.scalars().all():
        await session.delete(emb)

    await session.delete(correction)
    await session.commit()
    return {"deleted": correction_id}


@router.delete("/embeddings", summary="Clear all embeddings (reset knowledge base)")
async def clear_embeddings(
    source_type: str | None = Query(None, description="'training' or 'correction' — omit to clear all"),
    session: AsyncSession = Depends(get_db),
):
    """Delete all RAG embeddings. Optionally filter by source_type."""
    stmt = select(RAGEmbedding)
    if source_type:
        stmt = stmt.where(RAGEmbedding.source_type == source_type)
    result = await session.execute(stmt)
    rows = result.scalars().all()
    count = len(rows)
    for row in rows:
        await session.delete(row)
    await session.commit()
    logger.info("Cleared %d RAG embeddings (source_type=%s)", count, source_type or "all")
    return {"deleted_embeddings": count}
