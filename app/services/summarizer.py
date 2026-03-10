from __future__ import annotations

import json

from app.core.config import Settings
from app.services.llm_client import LLMClient
from app.services.prompt_loader import PromptLibrary


class Summarizer:
    def __init__(self, llm_client: LLMClient, settings: Settings) -> None:
        self.llm_client = llm_client
        self.prompts = PromptLibrary(settings)

    def summarize(self, text: str, language: str = "zh") -> dict:
        summary_style = self.prompts.get("summarizer_style")
        system_prompt = (
            "You summarize source material into strict JSON with fields: "
            "summary, outline, highlights, tags, title_candidates.\n"
            f"{summary_style}"
        )
        user_prompt = (
            f"Language: {language}\n"
            "Return JSON only.\n"
            "Need 3 Chinese title candidates, a summary under 120 Chinese characters, "
            "3-5 outline items, 3-5 highlights, and 3-6 tags.\n"
            "Title candidates should sound like a thoughtful公众号 writer, not clickbait headlines.\n"
            "Highlights should prioritize trend signals, structural changes, overlooked details, and restrained judgment.\n"
            f"Source:\n{text}"
        )
        response = self.llm_client.chat(system_prompt, user_prompt)
        if response.startswith("LLM_FALLBACK::"):
            seed = text[:120]
            return {
                "summary": f"{seed[:100]}..." if len(seed) > 100 else seed,
                "outline": ["表层信息之外的变化", "真正值得注意的结构信号", "拉长时间后的判断"],
                "highlights": ["很多变化的关键不在新闻本身，而在背后的结构变化", "如果把时间拉长，细节里往往藏着更重要的趋势信号", "判断可以有，但不必写得过满"],
                "tags": ["长期趋势", "结构变化", "内容观察", "公众号写作"],
                "title_candidates": [
                    "这件事真正值得注意的，不只是表面信息",
                    "如果拉长时间看，变化可能才刚刚开始",
                    "很多人忽略的细节，恰好透露了方向",
                ],
            }
        return json.loads(response)
