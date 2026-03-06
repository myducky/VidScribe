from pathlib import Path

from app.core.config import get_settings
from app.core.errors import InvalidMediaError
from app.core.enums import InputType, JobStatus
from app.schemas.common import CoverSchema, JobResultSchema, SourceSchema
from app.services.job_service import JobService


def _fake_video_result(file_path: Path) -> JobResultSchema:
    return JobResultSchema(
        job_id="video-job",
        input_type=InputType.UPLOADED_VIDEO,
        status=JobStatus.SUCCESS,
        title_candidates=["视频分析结果"],
        summary="summary",
        outline=["背景", "要点", "结论"],
        highlights=["亮点"],
        tags=["视频"],
        article_markdown="# 视频分析结果",
        cover=CoverSchema(
            prompt="prompt",
            layout="layout",
            text_on_cover="封面",
        ),
        source=SourceSchema(
            language="zh",
            duration_sec=0,
            transcript_raw=str(file_path.name),
            transcript_clean=str(file_path.name),
        ),
    )


def test_analyze_video_sanitizes_uploaded_filename(client, monkeypatch):
    captured_path: Path | None = None

    def fake_run_video_analysis(_self: JobService, _db, file_path: Path) -> JobResultSchema:
        nonlocal captured_path
        captured_path = file_path
        return _fake_video_result(file_path)

    monkeypatch.setattr(JobService, "run_video_analysis", fake_run_video_analysis)

    response = client.post(
        "/v1/analyze-video",
        files={"file": ("../../evil.mp4", b"video-bytes", "video/mp4")},
    )

    assert response.status_code == 200
    assert captured_path is not None
    assert captured_path.parent == get_settings().storage_path / "uploads"
    assert captured_path.name != "evil.mp4"
    assert ".." not in captured_path.name
    assert captured_path.suffix == ".mp4"


def test_analyze_video_enforces_size_limit(client):
    settings = get_settings()
    original_limit = settings.max_upload_mb
    settings.max_upload_mb = 0
    try:
        response = client.post(
            "/v1/analyze-video",
            files={"file": ("clip.mp4", b"1", "video/mp4")},
        )
    finally:
        settings.max_upload_mb = original_limit

    assert response.status_code == 413
    assert response.json() == {"detail": "Uploaded file exceeds 0 MB limit."}


def test_analyze_video_returns_422_for_invalid_media(client, monkeypatch):
    def fake_run_video_analysis(_self: JobService, _db, _file_path: Path) -> JobResultSchema:
        raise InvalidMediaError("Uploaded file is not a valid or supported video.")

    monkeypatch.setattr(JobService, "run_video_analysis", fake_run_video_analysis)

    response = client.post(
        "/v1/analyze-video",
        files={"file": ("clip.mp4", b"not-a-real-video", "video/mp4")},
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "Uploaded file is not a valid or supported video."}
