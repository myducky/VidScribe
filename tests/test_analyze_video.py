import os
from pathlib import Path
import subprocess

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.errors import InvalidMediaError, RemoteVideoDownloadError
from app.core.enums import InputType, JobStatus
from app.models.job import Job
from app.schemas.common import CoverSchema, JobResultSchema, SourceSchema
from app.services.audio_extractor import AudioExtractor, resolve_ffmpeg_executable
from app.services.job_service import JobService
from app.services.transcriber import Transcriber


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
        article_html="<h1>视频分析结果</h1>",
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


def test_analyze_video_runs_primary_pipeline_successfully(client, monkeypatch, tmp_path):
    audio_path = tmp_path / "clip.mp3"
    audio_path.write_bytes(b"audio")

    monkeypatch.setattr(
        "app.services.audio_extractor.AudioExtractor.extract",
        lambda _self, _video_path, _output_dir: audio_path,
    )
    monkeypatch.setattr(
        "app.services.transcriber.Transcriber.transcribe",
        lambda _self, _audio_path: ("这是上传视频主链路里的转写文本。", "zh"),
    )

    response = client.post(
        "/v1/analyze-video",
        files={"file": ("clip.mp4", b"video-bytes", "video/mp4")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["input_type"] == "uploaded_video"
    assert body["status"] == JobStatus.SUCCESS.value
    assert body["source"]["transcript_raw"] == "这是上传视频主链路里的转写文本。"
    assert body["article_html"].startswith("<h1>")

    session = SessionLocal()
    try:
        job = session.query(Job).one()
        steps = {step.step_name: step.status.value for step in job.steps}
        assert job.status == JobStatus.SUCCESS
        assert steps["extract_audio"] == "SUCCESS"
        assert steps["transcribe_audio"] == "SUCCESS"
        assert steps["persist_artifacts"] == "SUCCESS"
        assert len(job.artifacts) == 3
    finally:
        session.close()


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


def test_analyze_video_returns_422_for_empty_transcript(client, monkeypatch, tmp_path):
    audio_path = tmp_path / "clip.mp3"
    audio_path.write_bytes(b"audio")

    monkeypatch.setattr(
        "app.services.audio_extractor.AudioExtractor.extract",
        lambda _self, _video_path, _output_dir: audio_path,
    )
    monkeypatch.setattr(
        "app.services.transcriber.Transcriber.transcribe",
        lambda _self, _audio_path: ("", "zh"),
    )

    response = client.post(
        "/v1/analyze-video",
        files={"file": ("clip.mp4", b"video-bytes", "video/mp4")},
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "No speech was transcribed from the video audio."}


def test_analyze_remote_video_returns_result_for_bilibili_url(client, monkeypatch):
    def fake_run_remote_video_analysis(_self: JobService, _db, payload) -> JobResultSchema:
        return JobResultSchema(
            job_id="remote-job",
            input_type=InputType.BILIBILI_URL,
            status=JobStatus.SUCCESS,
            title_candidates=["远程视频分析结果"],
            summary="summary",
            outline=["背景", "要点", "结论"],
            highlights=["亮点"],
            tags=["B站"],
            article_html="<h1>远程视频分析结果</h1>",
            cover=CoverSchema(
                prompt="prompt",
                layout="layout",
                text_on_cover="封面",
            ),
            source=SourceSchema(
                language="zh",
                duration_sec=0,
                transcript_raw=payload.video_url,
                transcript_clean=payload.video_url,
            ),
        )

    monkeypatch.setattr(JobService, "run_remote_video_analysis", fake_run_remote_video_analysis)

    response = client.post(
        "/v1/analyze-remote-video",
        json={"video_url": "https://www.bilibili.com/video/BV1S5PrzZEzQ"},
    )

    assert response.status_code == 200
    assert response.json()["input_type"] == "bilibili_url"
    assert response.json()["job_id"] == "remote-job"


def test_analyze_remote_video_runs_primary_pipeline_without_fallback(client, monkeypatch, tmp_path):
    downloaded_video = tmp_path / "remote.mp4"
    audio_path = tmp_path / "remote.mp3"
    downloaded_video.write_bytes(b"video")
    audio_path.write_bytes(b"audio")

    monkeypatch.setattr(
        "app.services.video_downloader.VideoDownloader.download_bilibili_video",
        lambda _self, _url, _output_dir: downloaded_video,
    )
    monkeypatch.setattr(
        "app.services.audio_extractor.AudioExtractor.extract",
        lambda _self, _video_path, _output_dir: audio_path,
    )
    monkeypatch.setattr(
        "app.services.transcriber.Transcriber.transcribe",
        lambda _self, _audio_path: ("这是远程视频主链路里的转写文本。", "zh"),
    )

    response = client.post(
        "/v1/analyze-remote-video",
        json={"video_url": "https://www.bilibili.com/video/BV1S5PrzZEzQ"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["input_type"] == "bilibili_url"
    assert body["status"] == JobStatus.SUCCESS.value
    assert body["source"]["transcript_raw"] == "这是远程视频主链路里的转写文本。"
    assert body["article_html"].startswith("<h1>")


def test_analyze_remote_video_returns_422_for_unsupported_platform(client, monkeypatch):
    def fake_run_remote_video_analysis(_self: JobService, _db, _payload) -> JobResultSchema:
        raise ValueError("Unsupported remote video URL. Use a public Bilibili link, or upload the video directly.")

    monkeypatch.setattr(JobService, "run_remote_video_analysis", fake_run_remote_video_analysis)

    response = client.post(
        "/v1/analyze-remote-video",
        json={"video_url": "https://example.com/video/123"},
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": "Unsupported remote video URL. Use a public Bilibili link, or upload the video directly."
    }


def test_analyze_remote_video_returns_503_for_remote_download_failure(client, monkeypatch):
    def fake_run_remote_video_analysis(_self: JobService, _db, _payload) -> JobResultSchema:
        raise RemoteVideoDownloadError("Bilibili download failed; use raw_text or uploaded_video fallback.")

    monkeypatch.setattr(JobService, "run_remote_video_analysis", fake_run_remote_video_analysis)

    response = client.post(
        "/v1/analyze-remote-video",
        json={"video_url": "https://www.bilibili.com/video/BV1S5PrzZEzQ"},
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "Bilibili download failed; use raw_text or uploaded_video fallback."}


def test_audio_extractor_falls_back_to_imageio_ffmpeg_binary(monkeypatch, tmp_path):
    extractor = AudioExtractor()
    video_path = tmp_path / "clip.mp4"
    video_path.write_bytes(b"video")
    output_dir = tmp_path / "audio"

    resolve_ffmpeg_executable.cache_clear()
    monkeypatch.setattr("app.services.audio_extractor.which", lambda _name: None)
    monkeypatch.setattr(
        "imageio_ffmpeg.get_ffmpeg_exe",
        lambda: "/tmp/fake-ffmpeg",
    )

    captured_command: list[str] = []

    def fake_run(command: list[str], capture_output: bool, text: bool, check: bool) -> subprocess.CompletedProcess[str]:
        nonlocal captured_command
        captured_command = command
        return subprocess.CompletedProcess(command, returncode=0, stdout="", stderr="")

    monkeypatch.setattr("app.services.audio_extractor.subprocess.run", fake_run)

    audio_path = extractor.extract(video_path, output_dir)

    assert captured_command[0] == "/tmp/fake-ffmpeg"
    assert audio_path == output_dir / "clip.mp3"
    resolve_ffmpeg_executable.cache_clear()


def test_transcriber_exposes_ffmpeg_alias_on_path(monkeypatch, tmp_path):
    settings = get_settings()
    original_storage_dir = settings.storage_dir
    original_path = os.environ.get("PATH", "")
    settings.storage_dir = str(tmp_path)

    try:
        resolve_ffmpeg_executable.cache_clear()
        monkeypatch.setattr(
            "app.services.audio_extractor.resolve_ffmpeg_executable",
            lambda: "/tmp/fake-ffmpeg-bin",
        )
        monkeypatch.setattr(
            "app.services.transcriber.resolve_ffmpeg_executable",
            lambda: "/tmp/fake-ffmpeg-bin",
        )

        transcriber = Transcriber(settings)
        transcriber._ensure_ffmpeg_on_path()

        ffmpeg_link = tmp_path / ".runtime-bin" / "ffmpeg"
        assert ffmpeg_link.is_symlink()
        assert os.readlink(ffmpeg_link) == "/tmp/fake-ffmpeg-bin"
        assert str(tmp_path / ".runtime-bin") in os.environ["PATH"].split(os.pathsep)
    finally:
        settings.storage_dir = original_storage_dir
        os.environ["PATH"] = original_path
        resolve_ffmpeg_executable.cache_clear()


def test_transcriber_passes_initial_prompt_to_whisper(monkeypatch, tmp_path):
    settings = get_settings()
    original_prompt = settings.whisper_initial_prompt
    settings.whisper_initial_prompt = "请优先识别星巴克和抖音。"

    captured_kwargs: dict[str, str] = {}

    class FakeModel:
        def transcribe(self, _audio_path: str, **kwargs: str) -> dict[str, str]:
            captured_kwargs.update(kwargs)
            return {"text": "转写文本", "language": "zh"}

    audio_path = tmp_path / "clip.mp3"
    audio_path.write_bytes(b"audio")

    try:
        transcriber = Transcriber(settings)
        monkeypatch.setattr(transcriber, "_ensure_ffmpeg_on_path", lambda: None)
        monkeypatch.setattr(transcriber, "_load_model", lambda: FakeModel())

        text, language = transcriber.transcribe(audio_path)

        assert text == "转写文本"
        assert language == "zh"
        assert captured_kwargs == {"initial_prompt": "请优先识别星巴克和抖音。"}
    finally:
        settings.whisper_initial_prompt = original_prompt
