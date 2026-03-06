from __future__ import annotations

from pathlib import Path

from app.core.celery_app import celery_app
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.job import Job
from app.schemas.requests import AnalyzeTextRequest
from app.services.job_service import JobService


@celery_app.task(name="app.tasks.jobs.process_job", ignore_result=True)
def process_job(job_id: str) -> dict:
    settings = get_settings()
    service = JobService(settings)
    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if job is None:
            raise ValueError(f"Job not found: {job_id}")

        input_payload = job.input_payload or {}
        if job.input_type.value == "raw_text":
            request = AnalyzeTextRequest(
                raw_text=input_payload["raw_text"],
                desired_length=input_payload.get("desired_length", 1200),
                language=input_payload.get("language", "zh"),
            )
            result = service.pipeline.run(
                db,
                job,
                raw_text=request.raw_text,
                desired_length=request.desired_length,
                language=request.language,
            )
        elif job.input_type.value == "douyin_url":
            file_path_value = input_payload.get("file_path")
            result = service.pipeline.run(
                db,
                job,
                douyin_url=input_payload["douyin_url"],
                raw_text=input_payload.get("raw_text"),
                file_path=Path(file_path_value) if file_path_value else None,
                desired_length=input_payload.get("desired_length", 1200),
                language=input_payload.get("language", "zh"),
            )
        else:
            file_path = input_payload.get("file_path") or input_payload.get("uploaded_video_path")
            result = service.pipeline.run(
                db,
                job,
                raw_text=input_payload.get("raw_text"),
                file_path=Path(file_path),
                desired_length=input_payload.get("desired_length", 1200),
                language=input_payload.get("language", "zh"),
            )
        return result.model_dump(mode="json")
    finally:
        db.close()
