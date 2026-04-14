"""
export.py - Excel export endpoint.

POST /api/jobs/{job_id}/export
  Generate Excel LIMS Load Sheet from extraction result.
  Returns the file as a download.
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db
from config import settings
from excel_writer.excel_generator import ExcelGenerator
from models.lims_models import LIMSJob, LIMSLoadSheet
from models.schemas import ExtractionResult, JobStatus

router = APIRouter(prefix="/api/jobs", tags=["export"])
logger = logging.getLogger(__name__)


@router.post("/{job_id}/export", summary="Generate and download Excel Load Sheet")
async def export_job(job_id: str, db: AsyncSession = Depends(get_db)):
    """
    Generate an Excel LIMS Load Sheet for the completed job.

    Returns the .xlsx file as a download attachment.
    If an Excel file already exists for this job, it is regenerated.
    """
    job = await _get_job_or_404(job_id, db)

    if job.status != JobStatus.COMPLETE.value:
        raise HTTPException(
            status_code=409,
            detail=f"Job is not complete (current status: '{job.status}'). "
                   "Wait for processing to finish before exporting.",
        )

    result_data = job.get_result()
    if not result_data:
        raise HTTPException(status_code=500, detail="No extraction data available for this job")

    # Rebuild ExtractionResult from stored JSON
    try:
        result = ExtractionResult(**result_data)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to deserialise result: {exc}") from exc

    # Generate Excel file
    output_filename = f"LIMS_LoadSheet_{job_id[:8]}.xlsx"
    output_path = settings.output_dir / output_filename

    generator = ExcelGenerator()
    generator.generate(
        result=result,
        output_path=output_path,
        validation_issues=result.validation_errors,
    )

    # Persist output path and increment download counter
    job.output_path = str(output_path)
    job.download_count = (job.download_count or 0) + 1
    db.add(
        LIMSLoadSheet(
            job_id=job_id,
            file_path=str(output_path),
        )
    )
    await db.commit()

    logger.info("Excel export ready for job %s: %s", job_id, output_path)

    return FileResponse(
        path=str(output_path),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=output_filename,
        headers={"Content-Disposition": f"attachment; filename={output_filename}"},
    )


# ── Helper ────────────────────────────────────────────────────────────────────

async def _get_job_or_404(job_id: str, db: AsyncSession) -> LIMSJob:
    job = await db.get(LIMSJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    return job
