import re


class TranscriptCleaner:
    def clean(self, text: str) -> str:
        text = re.sub(r"\s+", " ", text).strip()
        text = re.sub(r"([，。！？；：])\1+", r"\1", text)
        return text
