from __future__ import annotations

from textwrap import shorten

from openai import APIConnectionError, APIStatusError, AuthenticationError, OpenAI, RateLimitError

from app.core.config import Settings
from app.core.errors import LLMUnavailableError
from app.core.logging import logger


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
        logger.info(
            "LLM client initialized",
            extra={
                "llm_mode": self.mode,
                "llm_model": self.settings.openai_model,
                "llm_base_url": self.settings.openai_base_url or "https://api.openai.com/v1",
            },
        )

    @property
    def is_configured(self) -> bool:
        return self._client is not None

    @property
    def mode(self) -> str:
        return "real_llm" if self.is_configured else "fallback"

    @property
    def api_style(self) -> str:
        base_url = (self.settings.openai_base_url or "").rstrip("/")
        if base_url.endswith("/compatible-mode/v1"):
            return "chat_completions"
        return "responses"

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        if self._client is None:
            seed = shorten(user_prompt.replace("\n", " "), width=180, placeholder="...")
            logger.warning(
                "LLM request used fallback generator",
                extra={"llm_model": self.settings.openai_model},
            )
            return f"LLM_FALLBACK::{seed}"

        try:
            if self.api_style == "chat_completions":
                response = self._client.chat.completions.create(
                    model=self.settings.openai_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                )
                return response.choices[0].message.content or ""

            response = self._client.responses.create(
                model=self.settings.openai_model,
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except AuthenticationError as exc:
            raise LLMUnavailableError("LLM authentication failed. Check OPENAI_API_KEY.") from exc
        except RateLimitError as exc:
            raise LLMUnavailableError("LLM quota exceeded or rate limited. Check OpenAI billing and quota.") from exc
        except APIConnectionError as exc:
            raise LLMUnavailableError("LLM connection failed. Check network access to the configured OpenAI endpoint.") from exc
        except APIStatusError as exc:
            raise LLMUnavailableError(f"LLM request failed with upstream status {exc.status_code}.") from exc
        return response.output_text
