from __future__ import annotations

import json

from app.services.llm_client import LLMClient


class Summarizer:
    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client

    def summarize(self, text: str, language: str = "zh") -> dict:
        system_prompt = (
            "You summarize source material into strict JSON with fields: "
            "summary, outline, highlights, tags, title_candidates."
        )
        user_prompt = (
            f"Language: {language}\n"
            "Return JSON only.\n"
            "Need 3 Chinese title candidates, a summary under 120 Chinese characters, "
            "3-5 outline items, 3-5 highlights, and 3-6 tags.\n"
            f"Source:\n{text}"
        )
        response = self.llm_client.chat(system_prompt, user_prompt)
        if response.startswith("LLM_FALLBACK::"):
            seed = text[:120]
            return {
                "summary": f"{seed[:100]}..." if len(seed) > 100 else seed,
                "outline": ["内容背景", "核心观点", "可执行启发"],
                "highlights": ["保留原始事实语义", "结构化输出", "适配公众号文章"],
                "tags": ["短视频", "内容整理", "公众号写作"],
                "title_candidates": [
                    "从短视频内容提炼出一篇可发布文章",
                    "把口播和字幕整理成清晰公众号稿件",
                    "一次性完成摘要、提纲与正文生成",
                ],
            }
        return json.loads(response)
