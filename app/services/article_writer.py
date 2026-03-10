from __future__ import annotations

from app.core.config import Settings
from app.services.llm_client import LLMClient
from app.services.prompt_loader import PromptLibrary


class ArticleWriter:
    def __init__(self, llm_client: LLMClient, settings: Settings) -> None:
        self.llm_client = llm_client
        self.prompts = PromptLibrary(settings)

    def generate(self, text: str, structured_summary: dict, desired_length: int = 1200) -> str:
        author_persona = self.prompts.get("article_persona")
        writing_requirements = self.prompts.get("article_requirements")
        system_prompt = (
            "Write a Chinese WeChat official account article in Markdown.\n"
            f"{author_persona}\n\n"
            f"{writing_requirements}"
        )
        user_prompt = (
            f"Target length: {desired_length} Chinese characters.\n"
            "请根据下面的结构化信息和原始素材，写成一篇适合公众号发布的中文文章。\n"
            "优先写出判断、观察和结构变化，不要把原文机械改写成资讯播报。\n"
            f"Structured summary: {structured_summary}\n"
            f"Source text:\n{text}"
        )
        response = self.llm_client.chat(system_prompt, user_prompt)
        if response.startswith("LLM_FALLBACK::"):
            summary = structured_summary["summary"]
            highlights = structured_summary.get("highlights", [])
            observation = highlights[0] if highlights else "真正值得注意的地方，不在表面信息本身，而在它背后的结构变化。"
            second_point = highlights[1] if len(highlights) > 1 else "如果拉长时间看，很多变化都不是偶然波动，而是更长期趋势的一部分。"
            return (
                f"# {structured_summary['title_candidates'][0]}\n\n"
                f"{summary}\n\n"
                f"这件事真正值得注意的地方在于，{observation}\n\n"
                f"很多人会先盯着表层信息，但如果把时间维度稍微拉长一点看，往往会发现另一个细节：{second_point}\n\n"
                "这也是我更关心的部分。因为对内容判断来说，重要的通常不是某一个瞬间的热度，而是它背后反映出的结构性变化。"
                "一旦这个变化开始出现，后面的影响往往会沿着产业、用户习惯和资源分配慢慢展开。\n\n"
                "所以与其把它理解成一条需要立刻表态的新闻，不如把它当成一个观察窗口。"
                "它未必马上改变一切，但会提醒我们，原来那套默认前提，可能已经在松动。\n\n"
                "从写作上说，这类素材最怕两种处理方式：一种是把信息简单复述一遍，另一种是急着下过满的结论。"
                "更稳妥的写法，应该是在事实之上保留一点判断，但不要把判断写得太满。"
                "因为真正有价值的，不是态度有多强，而是能不能把变化的方向说清楚。\n\n"
                "这篇内容先整理到这里。它更像是一份阶段性观察，而不是终局结论。"
                "如果后续还有更多信号出现，再往下更新判断会更有意义。"
            )
        return response
