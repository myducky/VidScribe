from __future__ import annotations

from app.services.llm_client import LLMClient


class ArticleWriter:
    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client

    def generate(self, text: str, structured_summary: dict, desired_length: int = 1200) -> str:
        system_prompt = (
            "Write a Chinese WeChat official account article in Markdown. "
            "Keep it informative, clear, moderately polished, and faithful to the source."
        )
        user_prompt = (
            f"Target length: {desired_length} Chinese characters.\n"
            f"Structured summary: {structured_summary}\n"
            f"Source text:\n{text}"
        )
        response = self.llm_client.chat(system_prompt, user_prompt)
        if response.startswith("LLM_FALLBACK::"):
            summary = structured_summary["summary"]
            outline = structured_summary["outline"]
            outline_md = "\n".join(f"## {item}\n\n围绕“{item}”展开，结合原始内容整理重点信息。" for item in outline)
            return f"# {structured_summary['title_candidates'][0]}\n\n{summary}\n\n{outline_md}\n\n## 结语\n\n以上内容基于原始素材整理，适合继续人工审校后发布。"
        return response
