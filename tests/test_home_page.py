from app.web.home_page import render_home_page


def test_render_home_page_injects_api_prefix():
    html = render_home_page("/v1")

    assert "__API_PREFIX__" not in html
    assert "/v1/analyze-text" in html
    assert "/static/home.css" in html
    assert "/static/home.js" in html
    assert "最近记录" in html
    assert "复制 Markdown" in html
    assert "主阅读区。长内容优先在这里看" in html
