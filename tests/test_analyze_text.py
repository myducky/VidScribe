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
    assert body["article_markdown"].startswith("# ")
