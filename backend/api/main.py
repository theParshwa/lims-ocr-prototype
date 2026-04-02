"""
main.py - FastAPI application entry point.

Registers all routers, configures CORS, middleware, and lifecycle events.
Run with: uvicorn api.main:app --reload --port 8000
"""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Ensure backend root is on sys.path when running from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.dependencies import init_db
from api.routes import agent, config, export, processing, rag, refine, training, upload
from config import settings
from logging_module.audit_logger import configure_logging

configure_logging(log_level=settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    logger.info("Starting LIMS OCR API v%s", settings.app_version)
    await init_db()
    logger.info("Database initialised")
    yield
    logger.info("LIMS OCR API shutting down")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "AI-powered LIMS document processing system. "
        "Upload STP/PTP/SPEC documents and extract structured LIMS Load Sheet data."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(upload.router)
app.include_router(processing.router)
app.include_router(refine.router)
app.include_router(export.router)
app.include_router(training.router)
app.include_router(agent.router)
app.include_router(config.router)
app.include_router(rag.router)


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["system"], summary="Service health check")
async def health():
    return {
        "status": "ok",
        "version": settings.app_version,
        "ai_provider": settings.ai_provider,
    }


@app.get("/", tags=["system"])
async def root():
    return {
        "message": "LIMS OCR Document Processor API",
        "docs": "/docs",
        "health": "/health",
    }
