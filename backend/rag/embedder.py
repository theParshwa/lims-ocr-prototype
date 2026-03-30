"""
embedder.py - Generates text embeddings for RAG retrieval.

Primary:  OpenAI text-embedding-3-small (cheap, fast, 1536-dim)
Fallback: TF-IDF cosine similarity (no API needed, zero cost)
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import re
from collections import Counter
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Cache embeddings on disk to avoid re-calling the API for identical text
_CACHE_PATH = Path(__file__).parent.parent / "rag_embed_cache.json"
_cache: dict[str, list[float]] = {}
_cache_dirty = False


def _load_cache() -> None:
    global _cache
    if _CACHE_PATH.exists():
        try:
            _cache = json.loads(_CACHE_PATH.read_text())
        except Exception:
            _cache = {}


def _save_cache() -> None:
    global _cache_dirty
    if _cache_dirty:
        try:
            _CACHE_PATH.write_text(json.dumps(_cache))
            _cache_dirty = False
        except Exception:
            pass


_load_cache()


def _text_hash(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()


# ── OpenAI embedding ──────────────────────────────────────────────────────────

def _openai_embed(text: str) -> Optional[list[float]]:
    """Call OpenAI embedding API. Returns None on any failure."""
    try:
        from openai import OpenAI
        import os
        api_key = os.environ.get("OPENAI_API_KEY") or ""
        if not api_key:
            return None
        client = OpenAI(api_key=api_key)
        resp = client.embeddings.create(
            model="text-embedding-3-small",
            input=text[:8000],   # API limit safety
        )
        return resp.data[0].embedding
    except Exception as exc:
        logger.debug("OpenAI embedding failed: %s", exc)
        return None


# ── TF-IDF fallback ───────────────────────────────────────────────────────────

def _tokenise(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _tfidf_vector(text: str, vocab: list[str]) -> list[float]:
    tokens  = Counter(_tokenise(text))
    total   = sum(tokens.values()) or 1
    vec     = []
    for term in vocab:
        tf  = tokens.get(term, 0) / total
        idf = 1.0          # simplified: assume all terms equally informative
        vec.append(tf * idf)
    return vec


def _make_tfidf_vocab(texts: list[str]) -> list[str]:
    all_tokens: set[str] = set()
    for t in texts:
        all_tokens.update(_tokenise(t))
    return sorted(all_tokens)


# ── Public API ────────────────────────────────────────────────────────────────

def embed(text: str) -> list[float]:
    """
    Return an embedding vector for `text`.

    Tries OpenAI first; falls back to a simple TF-IDF bag-of-words vector
    computed over the text itself (dimension = unique token count, max 512).
    """
    key = _text_hash(text)
    if key in _cache:
        return _cache[key]

    vec = _openai_embed(text)

    if vec is None:
        # Fallback: bag-of-words over the text tokens (self-contained)
        tokens = _tokenise(text)
        vocab  = sorted(set(tokens))[:512]
        counts = Counter(tokens)
        total  = sum(counts.values()) or 1
        vec    = [counts.get(t, 0) / total for t in vocab]
        if not vec:
            vec = [0.0]

    global _cache_dirty
    _cache[key] = vec
    _cache_dirty = True
    _save_cache()
    return vec


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors (handles different lengths)."""
    min_len = min(len(a), len(b))
    if min_len == 0:
        return 0.0
    a, b = a[:min_len], b[:min_len]
    dot  = sum(x * y for x, y in zip(a, b))
    na   = math.sqrt(sum(x * x for x in a))
    nb   = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)
