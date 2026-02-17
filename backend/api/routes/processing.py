"""
processing.py - Job status polling and data retrieval endpoints.

GET  /api/jobs               - List all jobs
GET  /api/jobs/{job_id}      - Get job status and full extraction result
PUT  /api/jobs/{job_id}/data - Update (edit) extracted data
POST /api/jobs/{job_id}/reprocess - Reprocess from scratch
DELETE /api/jobs/{job_id}    - Delete job and associated files
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db
from models.lims_models import LIMSJob
from models.schemas import ExtractionResult, JobStatus

router = APIRouter(prefix="/api/jobs", tags=["processing"])
logger = logging.getLogger(__name__)


@router.get("", summary="List all processing jobs")
async def list_jobs(
    db: AsyncSession = Depends(get_db),
    limit: int = 50,
    offset: int = 0,
):
    """Return paginated list of all jobs."""
    result = await db.execute(
        select(LIMSJob).order_by(LIMSJob.created_at.desc()).offset(offset).limit(limit)
    )
    jobs = result.scalars().all()
    return {
        "jobs": [_job_summary(j) for j in jobs],
        "total": len(jobs),
    }


@router.get("/{job_id}", summary="Get job status and extraction data")
async def get_job(job_id: str, db: AsyncSession = Depends(get_db)):
    """
    Return full job details including extraction result.

    While status is 'pending' or 'extracting', result will be null.
    Poll this endpoint until status is 'complete' or 'failed'.
    """
    job = await _get_job_or_404(job_id, db)
    result_data = job.get_result()
    return {
        **_job_summary(job),
        "result": result_data,
        "error_message": job.error_message,
    }


@router.put("/{job_id}/data", summary="Update extracted data (user edits)")
async def update_job_data(
    job_id: str,
    payload: dict,
    db: AsyncSession = Depends(get_db),
):
    """
    Accept user-edited extraction data and persist it.

    The payload should be the full ExtractionResult JSON with modifications.
    Re-runs validation after saving.
    """
    job = await _get_job_or_404(job_id, db)

    if job.status not in (JobStatus.COMPLETE.value, JobStatus.VALIDATING.value):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot edit job in state '{job.status}'",
        )

    # Validate the incoming payload structure
    try:
        updated = ExtractionResult(**payload)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid data structure: {exc}") from exc

    # Re-run validation
    from validation.schema_validator import SchemaValidator
    from validation.cross_ref_validator import CrossRefValidator

    schema_issues = SchemaValidator().validate(updated)
    cross_issues = CrossRefValidator().validate(updated)
    updated.validation_errors = [i.to_dict() for i in schema_issues + cross_issues]

    job.set_result(updated.model_dump())
    job.updated_at = datetime.now(timezone.utc)
    await db.commit()

    return {
        "job_id": job_id,
        "status": "updated",
        "validation_error_count": len(updated.validation_errors),
    }


@router.post("/{job_id}/reprocess", summary="Reprocess a job from scratch")
async def reprocess_job(
    job_id: str,
    background_tasks,
    db: AsyncSession = Depends(get_db),
):
    """Reset job status to pending and re-run the full pipeline."""
    from fastapi import BackgroundTasks
    from api.routes.upload import _process_document

    job = await _get_job_or_404(job_id, db)
    job.status = JobStatus.PENDING.value
    job.error_message = None
    job.result_json = None
    await db.commit()

    background_tasks.add_task(
        _process_document, job_id, job.file_path, job.original_filename
    )

    return {"job_id": job_id, "status": "reprocessing"}


@router.delete("/{job_id}", summary="Delete a job and its files")
async def delete_job(job_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a job record.  Source and output files are also removed."""
    import os
    job = await _get_job_or_404(job_id, db)

    # Remove files
    for path in [job.file_path, job.output_path]:
        if path:
            try:
                os.remove(path)
            except OSError:
                pass

    await db.delete(job)
    await db.commit()
    return {"deleted": job_id}


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_job_or_404(job_id: str, db: AsyncSession) -> LIMSJob:
    job = await db.get(LIMSJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    return job


def _job_summary(job: LIMSJob) -> dict:
    return {
        "job_id": job.id,
        "filename": job.original_filename,
        "status": job.status,
        "document_type": job.document_type,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
        "output_path": job.output_path,
    }
