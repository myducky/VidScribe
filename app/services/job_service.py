from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.enums import InputType, JobStatus
from app.models.job import Job
from app.schemas.common import JobResultSchema
from app.schemas.requests import AnalyzeTextRequest, CreateJobRequest
from app.services.article_writer import ArticleWriter
from app.services.cover_prompt_generator import CoverPromptGenerator
from app.services.input_resolver import InputResolver
from app.services.llm_client import LLMClient
from app.services.pipeline import PipelineDependencies, PipelineService
from app.services.result_exporter import ResultExporter
from app.services.summarizer import Summarizer
from app.services.transcript_cleaner import TranscriptCleaner
from app.services.video_downloader import VideoDownloader
from app.services.audio_extractor import AudioExtractor
from app.services.transcriber import Transcriber
from app.utils.files import ensure_directory, resolve_upload_reference


class JobService:
    def __init__(self, settings: Settings) -> None:
        llm_client = LLMClient(settings)
        deps = PipelineDependencies(
            input_resolver=InputResolver(),
            video_downloader=VideoDownloader(),
            audio_extractor=AudioExtractor(),
            transcriber=Transcriber(settings),
            transcript_cleaner=TranscriptCleaner(),
            summarizer=Summarizer(llm_client),
            article_writer=ArticleWriter(llm_client),
            cover_prompt_generator=CoverPromptGenerator(llm_client),
            result_exporter=ResultExporter(),
        )
        self.pipeline = PipelineService(settings, deps)

    def create_job(self, db: Session, payload: CreateJobRequest) -> Job:
        input_payload = payload.model_dump(mode="json")
        if payload.uploaded_video_path:
            upload_dir = ensure_directory(self.pipeline.settings.storage_path / "uploads")
            file_path = resolve_upload_reference(upload_dir, payload.uploaded_video_path)
            if not file_path.is_file():
                raise ValueError("uploaded_video_path does not exist in storage/uploads")
            input_payload["uploaded_video_path"] = file_path.name
            input_payload["file_path"] = str(file_path)
        job = Job(
            input_type=payload.input_type,
            status=JobStatus.PENDING,
            input_payload=input_payload,
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        self.pipeline.initialize_job_steps(db, job)
        return job

    def mark_job_dispatch_failed(self, db: Session, job: Job, message: str) -> Job:
        job.status = JobStatus.FAILED
        job.error_message = message
        db.add(job)
        db.commit()
        db.refresh(job)
        return job

    def run_text_analysis(self, db: Session, payload: AnalyzeTextRequest) -> JobResultSchema:
        job = Job(input_type=InputType.RAW_TEXT, status=JobStatus.PENDING, input_payload=payload.model_dump(mode="json"))
        db.add(job)
        db.commit()
        db.refresh(job)
        return self.pipeline.run(
            db,
            job,
            raw_text=payload.raw_text,
            desired_length=payload.desired_length,
            language=payload.language,
        )

    def run_video_analysis(self, db: Session, file_path: Path) -> JobResultSchema:
        job = Job(
            input_type=InputType.UPLOADED_VIDEO,
            status=JobStatus.PENDING,
            input_payload={"file_path": str(file_path)},
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return self.pipeline.run(db, job, file_path=file_path)
