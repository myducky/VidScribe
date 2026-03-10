from types import SimpleNamespace

from app.core.config import Settings
from app.services.llm_client import LLMClient


def test_llm_client_uses_chat_completions_for_dashscope_compatible_base_url():
    client = LLMClient(
        Settings(
            OPENAI_API_KEY="test-key",
            OPENAI_BASE_URL="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
            OPENAI_MODEL="qwen-plus",
        )
    )

    captured: dict = {}

    def fake_create(*, model, messages):
        captured["model"] = model
        captured["messages"] = messages
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="chat-ok"))]
        )

    client._client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=fake_create))
    )

    response = client.chat("system", "user")

    assert client.api_style == "chat_completions"
    assert response == "chat-ok"
    assert captured["model"] == "qwen-plus"
    assert captured["messages"] == [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "user"},
    ]


def test_llm_client_uses_responses_api_for_default_openai_base_url():
    client = LLMClient(
        Settings(
            OPENAI_API_KEY="test-key",
            OPENAI_BASE_URL="https://api.openai.com/v1",
            OPENAI_MODEL="gpt-4o-mini",
        )
    )

    captured: dict = {}

    def fake_create(*, model, input):
        captured["model"] = model
        captured["input"] = input
        return SimpleNamespace(output_text="responses-ok")

    client._client = SimpleNamespace(
        responses=SimpleNamespace(create=fake_create)
    )

    response = client.chat("system", "user")

    assert client.api_style == "responses"
    assert response == "responses-ok"
    assert captured["model"] == "gpt-4o-mini"
    assert captured["input"] == [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "user"},
    ]
