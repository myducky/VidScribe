def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_home(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "VidScribe API" in response.text
    assert "/docs" in response.text
    assert "直接开始" in response.text
    assert "/v1/analyze-text" in response.text
    assert "/static/home.css" in response.text
    assert "/static/home.js" in response.text
    assert "最近记录" in response.text
    assert "复制 Markdown" in response.text


def test_health_versioned(client):
    response = client.get("/v1/health")
    assert response.status_code == 200
