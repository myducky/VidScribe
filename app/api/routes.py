from __future__ import annotations

from celery.exceptions import BackendStoreError
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from kombu.exceptions import OperationalError
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.errors import InvalidMediaError
from app.core.logging import logger
from app.models.job import Job
from app.schemas.common import JobResultSchema, JobStatusResponse, JobStepSchema
from app.schemas.requests import AnalyzeTextRequest, CreateJobRequest
from app.schemas.responses import AnalyzeTextResponse, AnalyzeVideoResponse, CreateJobResponse, HealthResponse, JobDetailResponse
from app.services.job_service import JobService
from app.tasks.jobs import process_job
from app.utils.files import generate_upload_filename

router = APIRouter()


def get_job_service(settings: Settings = Depends(get_settings)) -> JobService:
    return JobService(settings)


@router.get("/health", response_model=HealthResponse, tags=["system"])
def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(status="ok", app=settings.app_name)


@router.post("/jobs", response_model=CreateJobResponse, status_code=status.HTTP_202_ACCEPTED, tags=["jobs"])
def create_job(
    payload: CreateJobRequest,
    db: Session = Depends(get_db),
    service: JobService = Depends(get_job_service),
) -> CreateJobResponse:
    try:
        job = service.create_job(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    try:
        process_job.delay(job.id)
    except (OperationalError, BackendStoreError) as exc:
        message = "Job queue is unavailable. Start Redis and the Celery worker, then retry POST /v1/jobs."
        service.mark_job_dispatch_failed(db, job, message)
        logger.exception("Failed to enqueue job", extra={"job_id": job.id})
        raise HTTPException(status_code=503, detail=message) from exc
    return CreateJobResponse(job_id=job.id, status=job.status.value)


@router.get("/jobs/{job_id}", response_model=JobDetailResponse, tags=["jobs"])
def get_job(job_id: str, db: Session = Depends(get_db)) -> JobDetailResponse:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobDetailResponse(
        job_id=job.id,
        input_type=job.input_type,
        status=job.status,
        error_message=job.error_message,
        steps=[
            JobStepSchema(
                step_name=step.step_name,
                status=step.status,
                start_time=step.start_time,
                end_time=step.end_time,
                error_message=step.error_message,
                retry_count=step.retry_count,
            )
            for step in job.steps
        ],
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@router.get("/jobs/{job_id}/result", response_model=JobResultSchema, tags=["jobs"])
def get_job_result(job_id: str, db: Session = Depends(get_db)) -> JobResultSchema:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if not job.result_payload:
        raise HTTPException(status_code=404, detail="Job result not ready")
    return JobResultSchema.model_validate(job.result_payload)


@router.post("/analyze-text", response_model=AnalyzeTextResponse, tags=["analysis"])
def analyze_text(
    payload: AnalyzeTextRequest,
    db: Session = Depends(get_db),
    service: JobService = Depends(get_job_service),
) -> AnalyzeTextResponse:
    return AnalyzeTextResponse.model_validate(service.run_text_analysis(db, payload).model_dump(mode="json"))


@router.post("/analyze-video", response_model=AnalyzeVideoResponse, tags=["analysis"])
async def analyze_video(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    service: JobService = Depends(get_job_service),
) -> AnalyzeVideoResponse:
    target_dir = settings.storage_path / "uploads"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / generate_upload_filename(file.filename)
    max_bytes = settings.max_upload_mb * 1024 * 1024
    written_bytes = 0
    try:
        with target_path.open("wb") as buffer:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                written_bytes += len(chunk)
                if written_bytes > max_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                        detail=f"Uploaded file exceeds {settings.max_upload_mb} MB limit.",
                    )
                buffer.write(chunk)
    except HTTPException:
        target_path.unlink(missing_ok=True)
        raise
    finally:
        await file.close()
    logger.info(
        "Stored uploaded video",
        extra={"upload_path": str(target_path), "original_filename": file.filename, "size_bytes": written_bytes},
    )
    try:
        result = service.run_video_analysis(db, target_path)
    except InvalidMediaError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return AnalyzeVideoResponse.model_validate(result.model_dump(mode="json"))
