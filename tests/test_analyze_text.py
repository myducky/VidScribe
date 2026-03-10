from app.core.errors import LLMUnavailableError
from app.services.job_service import JobService


def test_analyze_text_works_end_to_end(client):
    payload = {
        "raw_text": "这是一段关于如何把短视频内容整理成公众号文章的文字。内容强调先提炼观点，再补充结构，最后完成适合发布的正文。",
        "desired_length": 1000,
        "language": "zh",
    }
    response = client.post("/v1/analyze-text", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["input_type"] == "raw_text"
    assert len(body["title_candidates"]) == 3
    assert body["summary"]
    assert body["article_html"].startswith("<h1>")


def test_analyze_text_returns_503_when_llm_unavailable(client, monkeypatch):
    def fake_run_text_analysis(_self: JobService, _db, _payload):
        raise LLMUnavailableError("LLM quota exceeded or rate limited. Check OpenAI billing and quota.")

    monkeypatch.setattr(JobService, "run_text_analysis", fake_run_text_analysis)

    response = client.post(
        "/v1/analyze-text",
        json={
            "raw_text": "这是一段用于验证 LLM 不可用时接口错误语义的文本内容，长度足够满足请求校验要求。",
            "desired_length": 1000,
            "language": "zh",
        },
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "LLM quota exceeded or rate limited. Check OpenAI billing and quota."}
