from __future__ import annotations

import re
from pathlib import Path

from app.core.config import Settings

SECTION_PATTERN = re.compile(
    r"^##\s+(?P<name>[a-z0-9_]+)\s*$\n(?P<body>.*?)(?=^##\s+[a-z0-9_]+\s*$|\Z)",
    re.MULTILINE | re.DOTALL,
)


class PromptLibrary:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def get(self, section: str) -> str:
        content = self.settings.writing_style_path.read_text(encoding="utf-8")
        sections = {
            match.group("name"): match.group("body").strip()
            for match in SECTION_PATTERN.finditer(content)
        }
        try:
            return sections[section]
        except KeyError as exc:
            raise ValueError(f"Missing prompt section: {section}") from exc
