from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.enums import ArtifactCleanupTarget
from app.models.job import Artifact, Job


@dataclass
class CleanupResult:
    job_id: str
    target: ArtifactCleanupTarget
    deleted_paths: list[str]
    missing_paths: list[str]


@dataclass
class ArtifactLocationResult:
    job_id: str
    job_dir: str
    job_dir_url: str
    downloads_dir: str
    audio_dir: str
    result_json_path: str
    transcript_clean_path: str
    article_html_path: str
    job_dir_exists: bool
    downloads_dir_exists: bool
    audio_dir_exists: bool
    result_json_exists: bool
    transcript_clean_exists: bool
    article_html_exists: bool


class JobArtifactManager:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def cleanup(self, db: Session, job_id: str, target: ArtifactCleanupTarget) -> CleanupResult:
        job = db.get(Job, job_id)
        if job is None:
            raise LookupError("Job not found")

        job_dir = self._resolve_job_dir(job_id)
        deleted_paths: list[str] = []
        missing_paths: list[str] = []

        if target == ArtifactCleanupTarget.MEDIA:
            for name in ("downloads", "audio"):
                self._delete_directory(job_dir / name, deleted_paths, missing_paths)
        else:
            self._delete_directory(job_dir, deleted_paths, missing_paths)
            for artifact in list(job.artifacts):
                db.delete(artifact)
            db.commit()

        return CleanupResult(
            job_id=job_id,
            target=target,
            deleted_paths=deleted_paths,
            missing_paths=missing_paths,
        )

    def locate(self, db: Session, job_id: str) -> ArtifactLocationResult:
        job = db.get(Job, job_id)
        if job is None:
            raise LookupError("Job not found")

        job_dir = self._resolve_job_dir(job_id)
        downloads_dir = job_dir / "downloads"
        audio_dir = job_dir / "audio"
        result_json_path = job_dir / "result.json"
        transcript_clean_path = job_dir / "transcript_clean.txt"
        article_html_path = job_dir / "article.html"

        return ArtifactLocationResult(
            job_id=job_id,
            job_dir=str(job_dir),
            job_dir_url=job_dir.as_uri(),
            downloads_dir=str(downloads_dir),
            audio_dir=str(audio_dir),
            result_json_path=str(result_json_path),
            transcript_clean_path=str(transcript_clean_path),
            article_html_path=str(article_html_path),
            job_dir_exists=job_dir.exists(),
            downloads_dir_exists=downloads_dir.exists(),
            audio_dir_exists=audio_dir.exists(),
            result_json_exists=result_json_path.exists(),
            transcript_clean_exists=transcript_clean_path.exists(),
            article_html_exists=article_html_path.exists(),
        )

    def _resolve_job_dir(self, job_id: str) -> Path:
        job_dir = (self.settings.storage_path / job_id).resolve()
        storage_root = self.settings.storage_path.resolve()
        if storage_root not in job_dir.parents:
            raise ValueError("Resolved job directory is outside storage root")
        return job_dir

    @staticmethod
    def _delete_directory(path: Path, deleted_paths: list[str], missing_paths: list[str]) -> None:
        if not path.exists():
            missing_paths.append(str(path))
            return
        shutil.rmtree(path)
        deleted_paths.append(str(path))
