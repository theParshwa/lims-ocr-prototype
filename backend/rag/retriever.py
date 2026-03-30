"""
retriever.py - Store and retrieve RAG embeddings from SQLite.

Two source types are stored:
  - "training"   : uploaded Load Sheet training examples
  - "correction" : user corrections captured when editing extracted data
"""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.lims_models import RAGEmbedding, CorrectionExample
from rag.embedder import embed, cosine_similarity

logger = logging.getLogger(__name__)

TOP_K = 5   # number of examples to retrieve


# ── Store ─────────────────────────────────────────────────────────────────────

async def store_embedding(
    session: AsyncSession,
    source_type: str,       # "training" | "correction"
    source_id: str,         # training example id or correction id
    text: str,              # the text to embed
    metadata: dict,         # extra info to return at retrieval time
) -> None:
    """Embed `text` and persist to the RAGEmbedding table."""
    vec = embed(text)
    row = RAGEmbedding(
        source_type=source_type,
        source_id=str(source_id),
        text=text[:2000],
        embedding_json=json.dumps(vec),
        metadata_json=json.dumps(metadata),
    )
    session.add(row)
    await session.commit()
    logger.info("Stored %s embedding (source_id=%s)", source_type, source_id)


async def retrieve_similar(
    session: AsyncSession,
    query_text: str,
    source_types: list[str] | None = None,
    top_k: int = TOP_K,
) -> list[dict[str, Any]]:
    """
    Return top-k most similar stored embeddings to `query_text`.

    Returns list of dicts:
      { source_type, source_id, text, similarity, metadata }
    """
    q_vec = embed(query_text)

    stmt = select(RAGEmbedding)
    if source_types:
        stmt = stmt.where(RAGEmbedding.source_type.in_(source_types))

    result = await session.execute(stmt)
    rows   = result.scalars().all()

    if not rows:
        return []

    scored = []
    for row in rows:
        try:
            vec  = json.loads(row.embedding_json)
            sim  = cosine_similarity(q_vec, vec)
            meta = json.loads(row.metadata_json) if row.metadata_json else {}
            scored.append({
                "source_type": row.source_type,
                "source_id":   row.source_id,
                "text":        row.text,
                "similarity":  round(sim, 4),
                "metadata":    meta,
            })
        except Exception as exc:
            logger.debug("Error scoring embedding %s: %s", row.id, exc)

    scored.sort(key=lambda x: x["similarity"], reverse=True)
    return scored[:top_k]


# ── Build prompt context from retrieved results ────────────────────────────────

def build_rag_context(retrieved: list[dict[str, Any]]) -> str:
    """
    Format retrieved examples into a prompt string.
    Corrections take priority — listed first.
    """
    if not retrieved:
        return ""

    corrections  = [r for r in retrieved if r["source_type"] == "correction"]
    training     = [r for r in retrieved if r["source_type"] == "training"]

    lines = ["=== RETRIEVED CONTEXT (most relevant examples) ===", ""]

    if corrections:
        lines.append("── User Corrections (high priority) ──")
        for r in corrections:
            meta = r["metadata"]
            lines.append(
                f"  Sheet: {meta.get('sheet_name','?')}  "
                f"Field: {meta.get('field_name','?')}  "
                f"Doc type: {meta.get('document_type','?')}"
            )
            lines.append(f"  AI extracted : {meta.get('original_value','?')}")
            lines.append(f"  Correct value: {meta.get('corrected_value','?')}")
            if meta.get("context_text"):
                lines.append(f"  Context      : {meta['context_text'][:120]}")
            lines.append(f"  Similarity   : {r['similarity']:.2f}")
            lines.append("")

    if training:
        lines.append("── Training Examples ──")
        for r in training:
            meta = r["metadata"]
            lines.append(f"  [{meta.get('name','example')}]  similarity={r['similarity']:.2f}")
            lines.append(f"  {r['text'][:300]}")
            lines.append("")

    lines.append("=== END RETRIEVED CONTEXT ===")
    return "\n".join(lines)
