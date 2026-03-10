from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import get_settings
from app.services.llm_client import LLMClient


def main() -> None:
    settings = get_settings()
    client = LLMClient(settings)
    payload = {
        "mode": client.mode,
        "model": settings.openai_model,
        "base_url": settings.openai_base_url or "https://api.openai.com/v1",
        "api_key_configured": bool(settings.openai_api_key),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))

    if not client.is_configured:
        print("LLM is not configured. Set OPENAI_API_KEY to enable real model calls.")
        return

    response = client.chat(
        "You are a concise assistant.",
        "Reply with exactly: ok",
    )
    print("probe_response=", response)


if __name__ == "__main__":
    main()
