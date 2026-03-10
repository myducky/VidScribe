from kombu.exceptions import OperationalError

from app.core.config import get_settings
from app.core.enums import JobStatus
from app.core.database import SessionLocal
from app.models.job import Artifact, Job
from app.tasks.jobs import process_job


def test_create_job_accepts_request(client, monkeypatch):
    captured_job_ids: list[str] = []

    def fake_delay(job_id: str) -> object:
        captured_job_ids.append(job_id)
        return object()

    monkeypatch.setattr(process_job, "delay", fake_delay)

    response = client.post(
        "/v1/jobs",
        json={
            "input_type": "raw_text",
            "raw_text": "这是一段可直接提交异步任务的示例文本，适合验证 jobs API、状态追踪与结果导出。" * 2,
        },
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == JobStatus.PENDING.value
    assert captured_job_ids == [payload["job_id"]]


def test_create_job_returns_clear_503_when_queue_unavailable(client, monkeypatch):
    def fake_delay(_: str) -> object:
        raise OperationalError("redis unavailable")

    monkeypatch.setattr(process_job, "delay", fake_delay)

    response = client.post(
        "/v1/jobs",
        json={
            "input_type": "raw_text",
            "raw_text": "这是一段用于验证队列异常处理的文本内容，长度足够触发完整的 jobs 创建流程。" * 2,
        },
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Job queue is unavailable. Start Redis and the Celery worker, then retry POST /v1/jobs."
    }

    session = SessionLocal()
    try:
        job = session.query(Job).one()
        assert job.status == JobStatus.FAILED
        assert job.error_message == response.json()["detail"]
    finally:
        session.close()


def test_create_job_rejects_nonexistent_uploaded_video_reference(client):
    response = client.post(
        "/v1/jobs",
        json={
            "input_type": "uploaded_video",
            "uploaded_video_path": "../../etc/passwd",
        },
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "uploaded_video_path does not exist in storage/uploads"}


def test_create_job_accepts_uploaded_video_reference_from_upload_dir(client, monkeypatch):
    captured_job_ids: list[str] = []

    def fake_delay(job_id: str) -> object:
        captured_job_ids.append(job_id)
        return object()

    monkeypatch.setattr(process_job, "delay", fake_delay)

    upload_dir = get_settings().storage_path / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    target = upload_dir / "example.mp4"
    target.write_bytes(b"video")

    response = client.post(
        "/v1/jobs",
        json={
            "input_type": "uploaded_video",
            "uploaded_video_path": "example.mp4",
        },
    )

    assert response.status_code == 202
    assert len(captured_job_ids) == 1


def test_create_job_accepts_douyin_url_with_raw_text_fallback(client, monkeypatch):
    captured_job_ids: list[str] = []

    def fake_delay(job_id: str) -> object:
        captured_job_ids.append(job_id)
        return object()

    monkeypatch.setattr(process_job, "delay", fake_delay)

    response = client.post(
        "/v1/jobs",
        json={
            "input_type": "douyin_url",
            "douyin_url": "https://www.douyin.com/video/test",
            "raw_text": "这是一段备用文本，用于在抖音下载失败后继续完成任务处理流程。" * 2,
        },
    )

    assert response.status_code == 202
    assert len(captured_job_ids) == 1


def test_create_job_accepts_bilibili_url_with_raw_text_fallback(client, monkeypatch):
    captured_job_ids: list[str] = []

    def fake_delay(job_id: str) -> object:
        captured_job_ids.append(job_id)
        return object()

    monkeypatch.setattr(process_job, "delay", fake_delay)

    response = client.post(
        "/v1/jobs",
        json={
            "input_type": "bilibili_url",
            "bilibili_url": "https://www.bilibili.com/video/BV1S5PrzZEzQ",
            "raw_text": "这是一段备用文本，用于在 B 站下载失败后继续完成任务处理流程。" * 2,
        },
    )

    assert response.status_code == 202
    assert len(captured_job_ids) == 1


def test_get_job_detail_and_result(client, db_session):
    job = Job(
        input_type="raw_text",
        status=JobStatus.SUCCESS,
        input_payload={"raw_text": "已完成的任务"},
        result_payload={
            "job_id": "result-job",
            "input_type": "raw_text",
            "status": "SUCCESS",
            "title_candidates": ["标题一", "标题二", "标题三"],
            "summary": "摘要",
            "outline": ["背景", "要点", "结论"],
            "highlights": ["亮点"],
            "tags": ["标签"],
            "article_html": "<h1>正文</h1>",
            "cover": {"prompt": "prompt", "layout": "layout", "text_on_cover": "封面"},
            "source": {
                "language": "zh",
                "duration_sec": 0,
                "transcript_raw": "原始文本",
                "transcript_clean": "清洗文本",
            },
        },
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    detail_response = client.get(f"/v1/jobs/{job.id}")
    result_response = client.get(f"/v1/jobs/{job.id}/result")

    assert detail_response.status_code == 200
    assert detail_response.json()["job_id"] == job.id
    assert detail_response.json()["status"] == JobStatus.SUCCESS.value

    assert result_response.status_code == 200
    assert result_response.json()["job_id"] == "result-job"
    assert result_response.json()["source"]["transcript_clean"] == "清洗文本"


def test_create_job_can_complete_full_async_pipeline(client, monkeypatch):
    queued_job_ids: list[str] = []

    def fake_delay(job_id: str) -> object:
        queued_job_ids.append(job_id)
        return object()

    monkeypatch.setattr(process_job, "delay", fake_delay)

    create_response = client.post(
        "/v1/jobs",
        json={
            "input_type": "raw_text",
            "raw_text": "这是一段用于验证异步任务主链路的文本内容，会经过创建任务、执行 pipeline、查询详情和拉取结果的完整流程。" * 2,
        },
    )

    assert create_response.status_code == 202
    job_id = create_response.json()["job_id"]
    assert queued_job_ids == [job_id]

    process_job(job_id)

    detail_response = client.get(f"/v1/jobs/{job_id}")
    result_response = client.get(f"/v1/jobs/{job_id}/result")

    assert detail_response.status_code == 200
    assert result_response.status_code == 200
    assert detail_response.json()["status"] == JobStatus.SUCCESS.value
    assert result_response.json()["job_id"] == job_id
    assert result_response.json()["input_type"] == "raw_text"
    assert result_response.json()["article_html"].startswith("<h1>")

    steps = {step["step_name"]: step["status"] for step in detail_response.json()["steps"]}
    assert steps["parse_input"] == "SUCCESS"
    assert steps["clean_transcript"] == "SUCCESS"
    assert steps["summarize_content"] == "SUCCESS"
    assert steps["generate_article"] == "SUCCESS"
    assert steps["persist_artifacts"] == "SUCCESS"


def test_cleanup_job_media_deletes_download_and_audio_directories(client, db_session):
    job = Job(
        input_type="bilibili_url",
        status=JobStatus.SUCCESS,
        input_payload={"bilibili_url": "https://www.bilibili.com/video/BV1S5PrzZEzQ"},
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    job_dir = get_settings().storage_path / job.id
    downloads_dir = job_dir / "downloads"
    audio_dir = job_dir / "audio"
    downloads_dir.mkdir(parents=True, exist_ok=True)
    audio_dir.mkdir(parents=True, exist_ok=True)
    (downloads_dir / "demo.mp4").write_bytes(b"video")
    (audio_dir / "demo.mp3").write_bytes(b"audio")

    response = client.delete(f"/v1/jobs/{job.id}/artifacts?target=media")

    assert response.status_code == 200
    payload = response.json()
    assert payload["job_id"] == job.id
    assert payload["target"] == "media"
    assert str(downloads_dir.resolve()) in payload["deleted_paths"]
    assert str(audio_dir.resolve()) in payload["deleted_paths"]
    assert not downloads_dir.exists()
    assert not audio_dir.exists()


def test_cleanup_job_all_deletes_job_directory_and_artifact_rows(client, db_session):
    job = Job(
        input_type="raw_text",
        status=JobStatus.SUCCESS,
        input_payload={"raw_text": "已完成任务"},
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    job_dir = get_settings().storage_path / job.id
    job_dir.mkdir(parents=True, exist_ok=True)
    result_path = job_dir / "result.json"
    result_path.write_text("{}", encoding="utf-8")
    db_session.add(
        Artifact(
            job_id=job.id,
            artifact_type="result_json",
            file_path=str(result_path),
            metadata_json={},
        )
    )
    db_session.commit()

    response = client.delete(f"/v1/jobs/{job.id}/artifacts?target=all")

    assert response.status_code == 200
    assert response.json()["target"] == "all"
    assert not job_dir.exists()

    db_session.refresh(job)
    assert job.artifacts == []


def test_cleanup_job_artifacts_returns_404_for_missing_job(client):
    response = client.delete("/v1/jobs/missing-job/artifacts?target=media")

    assert response.status_code == 404
    assert response.json() == {"detail": "Job not found"}


def test_locate_job_artifacts_returns_local_paths_and_file_url(client, db_session):
    job = Job(
        input_type="raw_text",
        status=JobStatus.SUCCESS,
        input_payload={"raw_text": "已完成任务"},
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    job_dir = get_settings().storage_path / job.id
    downloads_dir = job_dir / "downloads"
    downloads_dir.mkdir(parents=True, exist_ok=True)

    response = client.get(f"/v1/jobs/{job.id}/artifacts/location")

    assert response.status_code == 200
    payload = response.json()
    assert payload["job_id"] == job.id
    assert payload["job_dir"] == str(job_dir.resolve())
    assert payload["job_dir_url"] == job_dir.resolve().as_uri()
    assert payload["downloads_dir"] == str(downloads_dir.resolve())
    assert payload["job_dir_exists"] is True
    assert payload["downloads_dir_exists"] is True
