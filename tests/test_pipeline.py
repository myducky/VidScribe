from app.core.config import get_settings
from app.core.errors import EmptyTranscriptError
from app.core.enums import InputType, JobStatus, StepStatus
from app.models.job import Job
from app.services.job_service import JobService


def test_pipeline_marks_steps_success(db_session):
    settings = get_settings()
    service = JobService(settings)
    job = Job(input_type=InputType.RAW_TEXT, status=JobStatus.PENDING, input_payload={"raw_text": "这是一段足够长的原始文本内容，用于测试整个流程的步骤状态变化。" * 3})
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    result = service.pipeline.run(db_session, job, raw_text=job.input_payload["raw_text"])
    assert result.status == JobStatus.SUCCESS
    assert all(step.status in {StepStatus.SUCCESS, StepStatus.SKIPPED} for step in job.steps)


def test_pipeline_falls_back_to_raw_text_when_douyin_download_fails(db_session, monkeypatch):
    settings = get_settings()
    service = JobService(settings)
    job = Job(
        input_type=InputType.DOUYIN_URL,
        status=JobStatus.PENDING,
        input_payload={
            "douyin_url": "https://www.douyin.com/video/test",
            "raw_text": "这是一段可作为回退来源的文本内容，用于保证抖音解析失败后仍能完成文章生成。" * 2,
        },
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    monkeypatch.setattr(
        service.pipeline.deps.video_downloader,
        "download_douyin_video",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("download failed")),
    )

    result = service.pipeline.run(
        db_session,
        job,
        douyin_url=job.input_payload["douyin_url"],
        raw_text=job.input_payload["raw_text"],
    )

    download_step = next(step for step in job.steps if step.step_name == "download_video_if_possible")
    extract_step = next(step for step in job.steps if step.step_name == "extract_audio")
    transcribe_step = next(step for step in job.steps if step.step_name == "transcribe_audio")

    assert result.status == JobStatus.SUCCESS
    assert result.source.transcript_raw == job.input_payload["raw_text"]
    assert download_step.status == StepStatus.SKIPPED
    assert extract_step.status == StepStatus.SKIPPED
    assert transcribe_step.status == StepStatus.SKIPPED


def test_pipeline_falls_back_to_raw_text_when_bilibili_download_fails(db_session, monkeypatch):
    settings = get_settings()
    service = JobService(settings)
    job = Job(
        input_type=InputType.BILIBILI_URL,
        status=JobStatus.PENDING,
        input_payload={
            "bilibili_url": "https://www.bilibili.com/video/BV1S5PrzZEzQ",
            "raw_text": "这是一段可作为回退来源的文本内容，用于保证 B 站下载失败后仍能完成文章生成。" * 2,
        },
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    monkeypatch.setattr(
        service.pipeline.deps.video_downloader,
        "download_bilibili_video",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("download failed")),
    )

    result = service.pipeline.run(
        db_session,
        job,
        bilibili_url=job.input_payload["bilibili_url"],
        raw_text=job.input_payload["raw_text"],
    )

    download_step = next(step for step in job.steps if step.step_name == "download_video_if_possible")
    extract_step = next(step for step in job.steps if step.step_name == "extract_audio")
    transcribe_step = next(step for step in job.steps if step.step_name == "transcribe_audio")

    assert result.status == JobStatus.SUCCESS
    assert result.source.transcript_raw == job.input_payload["raw_text"]
    assert download_step.status == StepStatus.SKIPPED
    assert extract_step.status == StepStatus.SKIPPED
    assert transcribe_step.status == StepStatus.SKIPPED


def test_pipeline_falls_back_to_raw_text_when_uploaded_video_processing_fails(db_session, monkeypatch, tmp_path):
    settings = get_settings()
    service = JobService(settings)
    video_path = tmp_path / "clip.mp4"
    video_path.write_bytes(b"video")
    job = Job(
        input_type=InputType.UPLOADED_VIDEO,
        status=JobStatus.PENDING,
        input_payload={
            "file_path": str(video_path),
            "raw_text": "这是一段备用文本，用于在视频音频抽取失败时继续完成后续总结与写作流程。" * 2,
        },
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    monkeypatch.setattr(
        service.pipeline.deps.audio_extractor,
        "extract",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("ffmpeg failed")),
    )

    result = service.pipeline.run(
        db_session,
        job,
        file_path=video_path,
        raw_text=job.input_payload["raw_text"],
    )

    extract_step = next(step for step in job.steps if step.step_name == "extract_audio")
    transcribe_step = next(step for step in job.steps if step.step_name == "transcribe_audio")

    assert result.status == JobStatus.SUCCESS
    assert result.source.transcript_raw == job.input_payload["raw_text"]
    assert extract_step.status == StepStatus.SKIPPED
    assert transcribe_step.status == StepStatus.SKIPPED


def test_pipeline_falls_back_to_raw_text_when_transcription_fails(db_session, monkeypatch, tmp_path):
    settings = get_settings()
    service = JobService(settings)
    video_path = tmp_path / "clip.mp4"
    audio_path = tmp_path / "clip.wav"
    video_path.write_bytes(b"video")
    audio_path.write_bytes(b"audio")
    job = Job(
        input_type=InputType.UPLOADED_VIDEO,
        status=JobStatus.PENDING,
        input_payload={
            "file_path": str(video_path),
            "raw_text": "这是一段备用文本，用于在转写失败时继续完成后续总结与写作流程。" * 2,
        },
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    monkeypatch.setattr(service.pipeline.deps.audio_extractor, "extract", lambda *_args, **_kwargs: audio_path)
    monkeypatch.setattr(
        service.pipeline.deps.transcriber,
        "transcribe",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("whisper failed")),
    )

    result = service.pipeline.run(
        db_session,
        job,
        file_path=video_path,
        raw_text=job.input_payload["raw_text"],
    )

    extract_step = next(step for step in job.steps if step.step_name == "extract_audio")
    transcribe_step = next(step for step in job.steps if step.step_name == "transcribe_audio")

    assert result.status == JobStatus.SUCCESS
    assert result.source.transcript_raw == job.input_payload["raw_text"]
    assert extract_step.status == StepStatus.SUCCESS
    assert transcribe_step.status == StepStatus.SKIPPED


def test_pipeline_fails_when_transcription_returns_empty_without_fallback(db_session, monkeypatch, tmp_path):
    settings = get_settings()
    service = JobService(settings)
    video_path = tmp_path / "clip.mp4"
    audio_path = tmp_path / "clip.wav"
    video_path.write_bytes(b"video")
    audio_path.write_bytes(b"audio")
    job = Job(
        input_type=InputType.UPLOADED_VIDEO,
        status=JobStatus.PENDING,
        input_payload={"file_path": str(video_path)},
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    monkeypatch.setattr(service.pipeline.deps.audio_extractor, "extract", lambda *_args, **_kwargs: audio_path)
    monkeypatch.setattr(service.pipeline.deps.transcriber, "transcribe", lambda *_args, **_kwargs: ("   ", "zh"))

    try:
        service.pipeline.run(
            db_session,
            job,
            file_path=video_path,
        )
    except EmptyTranscriptError as exc:
        assert str(exc) == "No speech was transcribed from the video audio."
    else:
        raise AssertionError("Expected EmptyTranscriptError for empty transcription output")

    db_session.refresh(job)
    transcribe_step = next(step for step in job.steps if step.step_name == "transcribe_audio")
    assert job.status == JobStatus.FAILED
    assert transcribe_step.status == StepStatus.FAILED


def test_pipeline_falls_back_to_uploaded_video_when_douyin_download_fails(db_session, monkeypatch, tmp_path):
    settings = get_settings()
    service = JobService(settings)
    video_path = tmp_path / "fallback.mp4"
    audio_path = tmp_path / "fallback.wav"
    video_path.write_bytes(b"video")
    audio_path.write_bytes(b"audio")
    job = Job(
        input_type=InputType.DOUYIN_URL,
        status=JobStatus.PENDING,
        input_payload={
            "douyin_url": "https://www.douyin.com/video/test",
            "file_path": str(video_path),
        },
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    monkeypatch.setattr(
        service.pipeline.deps.video_downloader,
        "download_douyin_video",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("download failed")),
    )
    monkeypatch.setattr(service.pipeline.deps.audio_extractor, "extract", lambda *_args, **_kwargs: audio_path)
    monkeypatch.setattr(
        service.pipeline.deps.transcriber,
        "transcribe",
        lambda *_args, **_kwargs: ("这是视频回退后的转写文本。", "zh"),
    )

    result = service.pipeline.run(
        db_session,
        job,
        douyin_url=job.input_payload["douyin_url"],
        file_path=video_path,
    )

    download_step = next(step for step in job.steps if step.step_name == "download_video_if_possible")
    extract_step = next(step for step in job.steps if step.step_name == "extract_audio")
    transcribe_step = next(step for step in job.steps if step.step_name == "transcribe_audio")

    assert result.status == JobStatus.SUCCESS
    assert result.source.transcript_raw == "这是视频回退后的转写文本。"
    assert download_step.status == StepStatus.SKIPPED
    assert extract_step.status == StepStatus.SUCCESS
    assert transcribe_step.status == StepStatus.SUCCESS


def test_pipeline_falls_back_to_uploaded_video_when_bilibili_download_fails(db_session, monkeypatch, tmp_path):
    settings = get_settings()
    service = JobService(settings)
    video_path = tmp_path / "fallback.mp4"
    audio_path = tmp_path / "fallback.wav"
    video_path.write_bytes(b"video")
    audio_path.write_bytes(b"audio")
    job = Job(
        input_type=InputType.BILIBILI_URL,
        status=JobStatus.PENDING,
        input_payload={
            "bilibili_url": "https://www.bilibili.com/video/BV1S5PrzZEzQ",
            "file_path": str(video_path),
        },
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    monkeypatch.setattr(
        service.pipeline.deps.video_downloader,
        "download_bilibili_video",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("download failed")),
    )
    monkeypatch.setattr(service.pipeline.deps.audio_extractor, "extract", lambda *_args, **_kwargs: audio_path)
    monkeypatch.setattr(
        service.pipeline.deps.transcriber,
        "transcribe",
        lambda *_args, **_kwargs: ("这是 B 站视频回退后的转写文本。", "zh"),
    )

    result = service.pipeline.run(
        db_session,
        job,
        bilibili_url=job.input_payload["bilibili_url"],
        file_path=video_path,
    )

    download_step = next(step for step in job.steps if step.step_name == "download_video_if_possible")
    extract_step = next(step for step in job.steps if step.step_name == "extract_audio")
    transcribe_step = next(step for step in job.steps if step.step_name == "transcribe_audio")

    assert result.status == JobStatus.SUCCESS
    assert result.source.transcript_raw == "这是 B 站视频回退后的转写文本。"
    assert download_step.status == StepStatus.SKIPPED
    assert extract_step.status == StepStatus.SUCCESS
    assert transcribe_step.status == StepStatus.SUCCESS
