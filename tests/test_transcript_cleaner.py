from app.core.config import Settings
from app.core.errors import LLMUnavailableError
from app.services.transcript_cleaner import TranscriptCleaner


class StubLLMClient:
    def __init__(self, response: str = "") -> None:
        self.response = response
        self.calls: list[tuple[str, str]] = []
        self.is_configured = True

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        self.calls.append((system_prompt, user_prompt))
        return self.response


def test_transcript_cleaner_uses_llm_to_refine_chinese_transcript():
    llm = StubLLMClient("今天去星巴克喝咖啡感觉还不错。然后聊到抖音电商这个事情。")
    cleaner = TranscriptCleaner(llm, Settings())

    cleaned = cleaner.clean("今天去新马克喝咖啡感觉还不错然后聊到豆音电商这个事情", language="zh")

    assert cleaned == "今天去星巴克喝咖啡感觉还不错。然后聊到抖音电商这个事情。"
    system_prompt, user_prompt = llm.calls[0]
    assert "Chinese ASR transcript editor" in system_prompt
    assert "ecommerce" in system_prompt
    assert "只输出校正后的正文" in user_prompt
    assert "不要洗稿" in user_prompt
    assert "数字表达错误" in user_prompt
    assert "星巴克" in user_prompt
    assert "抖音" in user_prompt


def test_transcript_cleaner_falls_back_to_rules_when_llm_is_unavailable():
    class UnavailableLLMClient:
        is_configured = True

        def chat(self, _system_prompt: str, _user_prompt: str) -> str:
            raise LLMUnavailableError("upstream unavailable")

    cleaner = TranscriptCleaner(UnavailableLLMClient(), Settings())

    cleaned = cleaner.clean(
        "今天去新马克喝咖啡感觉还不错然后聊到豆音电商这个事情其实增长已经慢下来了但是门店效率在提升",
        language="zh",
    )

    assert cleaned == "今天去星巴克喝咖啡感觉还不错。然后聊到抖音电商这个事情，其实增长已经慢下来了。但是门店效率在提升。"


def test_transcript_cleaner_skips_llm_for_non_chinese_language():
    llm = StubLLMClient("This should not be used.")
    cleaner = TranscriptCleaner(llm, Settings())

    cleaned = cleaner.clean("first line\nsecond line", language="en")

    assert cleaned == "first line。second line。"
    assert llm.calls == []
