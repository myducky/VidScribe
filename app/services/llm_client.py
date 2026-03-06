from __future__ import annotations

from textwrap import shorten

from openai import OpenAI

from app.core.config import Settings


class LLMClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client = None
        if settings.openai_api_key:
            self._client = OpenAI(
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url or None,
                timeout=settings.openai_timeout_sec,
            )

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        if self._client is None:
            seed = shorten(user_prompt.replace("\n", " "), width=180, placeholder="...")
            return f"LLM_FALLBACK::{seed}"

        response = self._client.responses.create(
            model=self.settings.openai_model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.output_text
