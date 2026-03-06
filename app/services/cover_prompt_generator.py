from __future__ import annotations

from app.services.llm_client import LLMClient


class CoverPromptGenerator:
    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client

    def generate(self, title: str, summary: str) -> dict:
        system_prompt = "Generate a concise cover concept for a Chinese article."
        user_prompt = (
            "Return JSON-like plain text concept for a Chinese article cover.\n"
            f"Title: {title}\nSummary: {summary}"
        )
        response = self.llm_client.chat(system_prompt, user_prompt)
        if response.startswith("LLM_FALLBACK::"):
            return {
                "prompt": f"中文封面概念：围绕“{title}”设计简洁专业的内容运营风格封面，突出信息提炼感。",
                "layout": "大标题居中，底部辅以 1 行摘要，留白充足",
                "text_on_cover": title[:14],
                "image_prompt_en": f"Editorial cover, modern Chinese content marketing style, clean typography, theme: {title}",
            }
        return {
            "prompt": response,
            "layout": "大标题居中，副标题弱化",
            "text_on_cover": title[:14],
            "image_prompt_en": f"Editorial cover for article about {title}",
        }
