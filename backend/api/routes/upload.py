"""
upload.py - File upload endpoint.

POST /api/upload
  Accepts multipart file uploads (PDF, DOCX).
  Saves files to disk, creates a job record, returns job ID.
  Processing is triggered asynchronously via a background task.
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

import aiofiles
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db
from config import settings
from models.lims_models import LIMSJob
from models.schemas import JobStatus

router = APIRouter(prefix="/api", tags=["upload"])
logger = logging.getLogger(__name__)

MAX_BYTES = settings.max_upload_size_mb * 1024 * 1024


@router.post("/upload", summary="Upload one or more LIMS documents for processing")
async def upload_documents(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(..., description="PDF or DOCX files"),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload documents and start async extraction pipeline.

    Returns a list of job descriptors, each containing:
    - job_id  (use to poll /api/jobs/{job_id} for progress)
    - filename
    - status  ("pending")
    """
    created_jobs = []

    for upload_file in files:
        # Validate extension
        suffix = Path(upload_file.filename or "").suffix.lower()
        if suffix not in settings.allowed_extensions:
            raise HTTPException(
                status_code=422,
                detail=f"Unsupported file type: '{suffix}'. Allowed: {settings.allowed_extensions}",
            )

        # Read content and check size
        content = await upload_file.read()
        if len(content) > MAX_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"File too large ({len(content) // 1024 // 1024} MB). Max: {settings.max_upload_size_mb} MB",
            )

        # Save to disk
        job_id = str(uuid.uuid4())
        safe_name = f"{job_id}{suffix}"
        file_path = settings.upload_dir / safe_name

        async with aiofiles.open(file_path, "wb") as fh:
            await fh.write(content)

        # Persist job to DB
        job = LIMSJob(
            id=job_id,
            filename=safe_name,
            original_filename=upload_file.filename or safe_name,
            file_path=str(file_path),
            status=JobStatus.PENDING.value,
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)

        logger.info("Uploaded file %s → job %s", upload_file.filename, job_id)

        # Schedule background processing
        background_tasks.add_task(_process_document, job_id, str(file_path), upload_file.filename or "")

        created_jobs.append({
            "job_id": job_id,
            "filename": upload_file.filename,
            "status": JobStatus.PENDING.value,
        })

    return {"jobs": created_jobs, "count": len(created_jobs)}


# ── Background processing task ────────────────────────────────────────────────

async def _process_document(job_id: str, file_path: str, document_name: str) -> None:
    """Background task: run the full extraction pipeline for one job."""
    import asyncio
    from api.dependencies import AsyncSessionLocal
    from extraction.pipeline import ExtractionPipeline
    from mapping.lims_mapper import LIMSMapper
    from training.excel_parser import build_training_prompt_context
    from training.training_manager import TrainingManager
    from validation.schema_validator import SchemaValidator
    from validation.cross_ref_validator import CrossRefValidator

    pipeline = ExtractionPipeline(
        ocr_enabled=settings.ocr_enabled,
        ocr_language=settings.ocr_language,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )

    async with AsyncSessionLocal() as db:
        # Update status to extracting
        job = await db.get(LIMSJob, job_id)
        if not job:
            return
        job.status = JobStatus.EXTRACTING.value
        await db.commit()

        try:
            # Load training context (few-shot examples from stored Load Sheets)
            training_examples = await TrainingManager().get_all_parsed(db)
            training_context = build_training_prompt_context(training_examples)

            # Run pipeline in thread pool (it's synchronous/blocking)
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: pipeline.run(file_path, job_id, document_name, training_context=training_context),
            )

            # Apply mapping rules
            mapper = LIMSMapper()
            result = mapper.apply(result)

            # Run validation
            schema_issues = SchemaValidator().validate(result)
            cross_issues = CrossRefValidator().validate(result)
            all_issues = [i.to_dict() for i in schema_issues + cross_issues]
            result.validation_errors = all_issues

            # Persist result
            job.status = result.status.value
            job.document_type = result.document_type
            job.set_result(result.model_dump())
            await db.commit()

            logger.info("Job %s complete. Status: %s", job_id, result.status)

        except Exception as exc:  # noqa: BLE001
            logger.exception("Job %s failed: %s", job_id, exc)
            job.status = JobStatus.FAILED.value
            job.error_message = str(exc)
            await db.commit()
