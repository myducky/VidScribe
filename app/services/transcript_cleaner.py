from __future__ import annotations

import re

from app.core.errors import LLMUnavailableError
from app.core.logging import logger
from app.core.config import Settings
from app.services.llm_client import LLMClient
from app.services.prompt_loader import PromptLibrary


class TranscriptCleaner:
    _PHRASE_REPLACEMENTS: tuple[tuple[str, str], ...] = (
        ("新马克", "星巴克"),
        ("新巴克", "星巴克"),
        ("星八克", "星巴克"),
        ("豆音", "抖音"),
        ("斗音", "抖音"),
        ("瑞辛", "瑞幸"),
        ("小红书书", "小红书"),
    )
    _STRONG_BREAK_MARKERS: tuple[str, ...] = (
        "然后",
        "后来",
        "但是",
        "不过",
        "所以",
        "因此",
        "另外",
        "同时",
        "最后",
    )
    _WEAK_BREAK_MARKERS: tuple[str, ...] = (
        "其实",
        "比如",
        "例如",
        "因为",
        "如果",
        "而且",
        "并且",
        "那么",
        "就是",
    )
    _PUNCTUATION = "，。！？；："
    _TERMINAL_PUNCTUATION = "。！？"

    def __init__(self, llm_client: LLMClient | None = None, settings: Settings | None = None) -> None:
        self.llm_client = llm_client
        self.prompts = PromptLibrary(settings) if settings is not None else None

    def clean(self, text: str, language: str = "zh") -> str:
        cleaned = self._rule_clean(text)
        if not cleaned:
            return ""
        if self._should_use_llm(language):
            refined = self._refine_with_llm(cleaned)
            if refined:
                return refined
        return cleaned

    def _should_use_llm(self, language: str) -> bool:
        if not language.lower().startswith("zh"):
            return False
        if self.llm_client is None or self.prompts is None:
            return False
        return bool(getattr(self.llm_client, "is_configured", True))

    def _refine_with_llm(self, text: str) -> str | None:
        assert self.prompts is not None
        assert self.llm_client is not None

        system_prompt = self.prompts.get("transcript_refiner_style")
        user_prompt = (
            "请校正下面这段中文 ASR 转写文本。\n"
            "要求：\n"
            "1. 修正明显同音错字、听错词、品牌名错误、平台名错误、产品名错误、数字表达错误、口语转写错误。\n"
            "2. 补充自然的中文断句和标点，但不要为了通顺而重写句子。\n"
            "3. 保留原意、原有信息量和说话风格，不要扩写，不要总结，不要洗稿。\n"
            "4. 遇到抖音、电商、品牌、消费、财经语境时，优先按最常见、最符合上下文的专有名词和术语校正。\n"
            "5. 如果原文存在歧义，选择最可能的日常中文表达；如果无法确定，也不要编造新事实。\n"
            "6. 只输出校正后的正文，不要标题，不要解释，不要项目符号。\n\n"
            f"原文：\n{text}"
        )

        try:
            response = self.llm_client.chat(system_prompt, user_prompt)
        except LLMUnavailableError as exc:
            logger.warning("Transcript refinement skipped because LLM is unavailable", extra={"error": str(exc)})
            return None

        refined = self._extract_refined_text(response)
        if not refined:
            logger.warning("Transcript refinement returned empty content; using rule-based cleanup")
            return None

        return self._rule_clean(refined)

    def _extract_refined_text(self, response: str) -> str:
        text = response.strip()
        text = re.sub(r"^```(?:text|markdown)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        text = re.sub(r"^(校正后文本|修正后文本|润色后文本)[:：]\s*", "", text)
        return text.strip()

    def _rule_clean(self, text: str) -> str:
        cleaned = self._normalize_whitespace(text)
        cleaned = self._apply_phrase_replacements(cleaned)
        cleaned = self._normalize_punctuation(cleaned)
        cleaned = self._insert_breaks(cleaned)
        cleaned = self._normalize_punctuation(cleaned)
        return self._ensure_terminal_punctuation(cleaned)

    def _normalize_whitespace(self, text: str) -> str:
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"\n+", "。", text)
        text = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _apply_phrase_replacements(self, text: str) -> str:
        for wrong, correct in self._PHRASE_REPLACEMENTS:
            text = text.replace(wrong, correct)
        return text

    def _normalize_punctuation(self, text: str) -> str:
        text = (
            text.replace(",", "，")
            .replace(".", "。")
            .replace("?", "？")
            .replace("!", "！")
            .replace(";", "；")
            .replace(":", "：")
        )
        text = re.sub(r"([，。！？；：])\1+", r"\1", text)
        text = re.sub(r"([。！？])[。！？]+", r"\1", text)
        text = re.sub(r"[ ]+([，。！？；：])", r"\1", text)
        text = re.sub(r"([（《“])\s+", r"\1", text)
        text = re.sub(r"\s+([）》”])", r"\1", text)
        return text.strip()

    def _insert_breaks(self, text: str) -> str:
        result: list[str] = []
        clause_length = 0
        sentence_length = 0
        index = 0

        while index < len(text):
            marker = self._match_marker(text, index)
            if marker and result and result[-1] not in self._PUNCTUATION:
                if marker in self._STRONG_BREAK_MARKERS and sentence_length >= 14:
                    result.append("。")
                    clause_length = 0
                    sentence_length = 0
                elif marker in self._WEAK_BREAK_MARKERS and clause_length >= 8:
                    result.append("，")
                    clause_length = 0

            char = text[index]
            result.append(char)
            if char in self._TERMINAL_PUNCTUATION:
                clause_length = 0
                sentence_length = 0
            elif char in "，；：":
                clause_length = 0
            elif not char.isspace():
                clause_length += 1
                sentence_length += 1
            index += 1

        return "".join(result)

    def _match_marker(self, text: str, index: int) -> str | None:
        for marker in (*self._STRONG_BREAK_MARKERS, *self._WEAK_BREAK_MARKERS):
            if text.startswith(marker, index):
                return marker
        return None

    def _ensure_terminal_punctuation(self, text: str) -> str:
        if not text:
            return ""
        if text[-1] in self._TERMINAL_PUNCTUATION:
            return text
        if text[-1] in "，；：":
            return f"{text[:-1]}。"
        return f"{text}。"
