from app.core.config import get_settings
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
