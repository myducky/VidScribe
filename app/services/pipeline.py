from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import EmptyTranscriptError
from app.core.enums import InputType, JobStatus, StepStatus
from app.core.logging import logger
from app.models.job import Artifact, Job, JobStep
from app.schemas.common import CoverSchema, JobResultSchema, SourceSchema
from app.services.article_writer import ArticleWriter
from app.services.audio_extractor import AudioExtractor
from app.services.cover_prompt_generator import CoverPromptGenerator
from app.services.input_resolver import InputResolver
from app.services.result_exporter import ResultExporter
from app.services.summarizer import Summarizer
from app.services.transcriber import Transcriber
from app.services.transcript_cleaner import TranscriptCleaner
from app.services.video_downloader import VideoDownloader

PIPELINE_STEPS = [
    "parse_input",
    "resolve_source",
    "download_video_if_possible",
    "extract_audio",
    "transcribe_audio",
    "clean_transcript",
    "summarize_content",
    "generate_article",
    "generate_cover_prompt",
    "persist_artifacts",
]


@dataclass
class PipelineDependencies:
    input_resolver: InputResolver
    video_downloader: VideoDownloader
    audio_extractor: AudioExtractor
    transcriber: Transcriber
    transcript_cleaner: TranscriptCleaner
    summarizer: Summarizer
    article_writer: ArticleWriter
    cover_prompt_generator: CoverPromptGenerator
    result_exporter: ResultExporter


class PipelineService:
    def __init__(self, settings: Settings, deps: PipelineDependencies) -> None:
        self.settings = settings
        self.deps = deps

    def initialize_job_steps(self, db: Session, job: Job) -> None:
        if job.steps:
            return
        for step_name in PIPELINE_STEPS:
            db.add(JobStep(job_id=job.id, step_name=step_name))
        db.commit()

    def _mark_step(
        self,
        db: Session,
        job: Job,
        step_name: str,
        status: StepStatus,
        *,
        error_message: str | None = None,
        increment_retry: bool = False,
    ) -> None:
        from datetime import datetime

        step = next(step for step in job.steps if step.step_name == step_name)
        now = datetime.utcnow()
        if status == StepStatus.RUNNING:
            step.start_time = now
        if status in {StepStatus.SUCCESS, StepStatus.FAILED, StepStatus.SKIPPED}:
            step.end_time = now
        if increment_retry:
            step.retry_count += 1
        step.status = status
        step.error_message = error_message
        db.add(step)
        db.commit()
        db.refresh(job)

    def run(
        self,
        db: Session,
        job: Job,
        *,
        raw_text: str | None = None,
        bilibili_url: str | None = None,
        douyin_url: str | None = None,
        file_path: Path | None = None,
        desired_length: int = 1200,
        language: str = "zh",
    ) -> JobResultSchema:
        self.initialize_job_steps(db, job)
        job.status = JobStatus.RUNNING
        db.add(job)
        db.commit()
        db.refresh(job)

        source_video: Path | None = file_path if job.input_type != InputType.RAW_TEXT else None
        transcript_raw = raw_text or ""
        source_language = language
        duration_sec = 0.0

        try:
            self._mark_step(db, job, "parse_input", StepStatus.RUNNING)
            self.deps.input_resolver.resolve(
                job.input_type,
                raw_text=raw_text,
                bilibili_url=bilibili_url,
                douyin_url=douyin_url,
                file_path=file_path,
            )
            self._mark_step(db, job, "parse_input", StepStatus.SUCCESS)

            self._mark_step(db, job, "resolve_source", StepStatus.RUNNING)
            self._mark_step(db, job, "resolve_source", StepStatus.SUCCESS)

            if job.input_type in {InputType.BILIBILI_URL, InputType.DOUYIN_URL}:
                self._mark_step(db, job, "download_video_if_possible", StepStatus.RUNNING)
                try:
                    if job.input_type == InputType.BILIBILI_URL:
                        source_video = self.deps.video_downloader.download_bilibili_video(
                            bilibili_url or "",
                            self.settings.storage_path / job.id / "downloads",
                        )
                    else:
                        source_video = self.deps.video_downloader.download_douyin_video(
                            douyin_url or "",
                            self.settings.storage_path / job.id / "downloads",
                        )
                except Exception as exc:
                    if not self._can_fallback_to_available_source(raw_text=raw_text, file_path=file_path):
                        raise
                    logger.warning(
                        "Remote video download failed; continuing with fallback source",
                        extra={"job_id": job.id, "error": str(exc), "input_type": job.input_type.value},
                    )
                    self._mark_step(
                        db,
                        job,
                        "download_video_if_possible",
                        StepStatus.SKIPPED,
                        error_message=str(exc),
                    )
                    source_video = file_path
                else:
                    self._mark_step(db, job, "download_video_if_possible", StepStatus.SUCCESS)
            else:
                self._mark_step(db, job, "download_video_if_possible", StepStatus.SKIPPED)

            if source_video is None:
                self._mark_step(db, job, "extract_audio", StepStatus.SKIPPED)
                self._mark_step(db, job, "transcribe_audio", StepStatus.SKIPPED)
            else:
                self._mark_step(db, job, "extract_audio", StepStatus.RUNNING)
                try:
                    audio_path = self.deps.audio_extractor.extract(source_video, self.settings.storage_path / job.id / "audio")
                except Exception as exc:
                    if raw_text:
                        logger.warning(
                            "Video processing failed during audio extraction; falling back to raw_text",
                            extra={"job_id": job.id, "error": str(exc)},
                        )
                        transcript_raw = raw_text
                        source_language = language
                        self._mark_step(
                            db,
                            job,
                            "extract_audio",
                            StepStatus.SKIPPED,
                            error_message=str(exc),
                        )
                        self._mark_step(
                            db,
                            job,
                            "transcribe_audio",
                            StepStatus.SKIPPED,
                            error_message="Used raw_text fallback after extract_audio failure.",
                        )
                    else:
                        raise
                else:
                    self._mark_step(db, job, "extract_audio", StepStatus.SUCCESS)

                    self._mark_step(db, job, "transcribe_audio", StepStatus.RUNNING)
                    try:
                        transcript_raw, source_language = self.deps.transcriber.transcribe(audio_path)
                        if not transcript_raw.strip():
                            raise EmptyTranscriptError("No speech was transcribed from the video audio.")
                    except Exception as exc:
                        if raw_text:
                            logger.warning(
                                "Video transcription failed; falling back to raw_text",
                                extra={"job_id": job.id, "error": str(exc)},
                            )
                            transcript_raw = raw_text
                            source_language = language
                            self._mark_step(
                                db,
                                job,
                                "transcribe_audio",
                                StepStatus.SKIPPED,
                                error_message=str(exc),
                            )
                        else:
                            raise
                    else:
                        self._mark_step(db, job, "transcribe_audio", StepStatus.SUCCESS)

            self._mark_step(db, job, "clean_transcript", StepStatus.RUNNING)
            transcript_clean = self.deps.transcript_cleaner.clean(transcript_raw, language=source_language)
            if not transcript_clean:
                raise EmptyTranscriptError("No usable transcript content was produced from the input.")
            self._mark_step(db, job, "clean_transcript", StepStatus.SUCCESS)

            self._mark_step(db, job, "summarize_content", StepStatus.RUNNING)
            structured_summary = self.deps.summarizer.summarize(transcript_clean, language=source_language)
            self._mark_step(db, job, "summarize_content", StepStatus.SUCCESS)

            self._mark_step(db, job, "generate_article", StepStatus.RUNNING)
            article_html = self.deps.article_writer.generate(
                transcript_clean,
                structured_summary,
                desired_length=desired_length,
            )
            self._mark_step(db, job, "generate_article", StepStatus.SUCCESS)

            self._mark_step(db, job, "generate_cover_prompt", StepStatus.RUNNING)
            cover = self.deps.cover_prompt_generator.generate(
                structured_summary["title_candidates"][0],
                structured_summary["summary"],
            )
            self._mark_step(db, job, "generate_cover_prompt", StepStatus.SUCCESS)

            result = JobResultSchema(
                job_id=job.id,
                input_type=job.input_type,
                status=JobStatus.SUCCESS,
                title_candidates=structured_summary["title_candidates"],
                summary=structured_summary["summary"],
                outline=structured_summary["outline"],
                highlights=structured_summary["highlights"],
                tags=structured_summary["tags"],
                article_html=article_html,
                cover=CoverSchema(**cover),
                source=SourceSchema(
                    language=source_language,
                    duration_sec=duration_sec,
                    transcript_raw=transcript_raw,
                    transcript_clean=transcript_clean,
                ),
            )

            self._mark_step(db, job, "persist_artifacts", StepStatus.RUNNING)
            job_dir = self.settings.storage_path / job.id
            result_path = self.deps.result_exporter.export_json(result, job_dir / "result.json")
            transcript_path = self.deps.result_exporter.export_text(transcript_clean, job_dir / "transcript_clean.txt")
            article_path = self.deps.result_exporter.export_text(article_html, job_dir / "article.html")
            db.add(Artifact(job_id=job.id, artifact_type="result_json", file_path=str(result_path), metadata_json={}))
            db.add(Artifact(job_id=job.id, artifact_type="transcript_clean", file_path=str(transcript_path), metadata_json={}))
            db.add(Artifact(job_id=job.id, artifact_type="article_html", file_path=str(article_path), metadata_json={}))
            self._mark_step(db, job, "persist_artifacts", StepStatus.SUCCESS)

            job.status = JobStatus.SUCCESS
            job.result_payload = result.model_dump(mode="json")
            db.add(job)
            db.commit()
            db.refresh(job)
            return result
        except Exception as exc:
            job.status = JobStatus.FAILED
            job.error_message = str(exc)
            db.add(job)
            db.commit()
            db.refresh(job)
            failed_steps = [step for step in job.steps if step.status == StepStatus.RUNNING]
            if failed_steps:
                self._mark_step(db, job, failed_steps[-1].step_name, StepStatus.FAILED, error_message=str(exc), increment_retry=True)
            raise

    @staticmethod
    def _can_fallback_to_available_source(*, raw_text: str | None, file_path: Path | None) -> bool:
        return bool(raw_text) or file_path is not None
