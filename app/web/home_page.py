from __future__ import annotations

from pathlib import Path

WEB_DIR = Path(__file__).resolve().parent
TEMPLATE_PATH = WEB_DIR / "templates" / "home.html"

def render_home_page(api_prefix: str) -> str:
    return TEMPLATE_PATH.read_text(encoding="utf-8").replace("__API_PREFIX__", api_prefix)
