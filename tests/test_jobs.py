from kombu.exceptions import OperationalError

from app.core.config import get_settings
from app.core.enums import JobStatus
from app.core.database import SessionLocal
from app.models.job import Job
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
