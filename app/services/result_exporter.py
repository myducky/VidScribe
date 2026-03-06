from __future__ import annotations

import json
from pathlib import Path

from app.schemas.common import JobResultSchema


class ResultExporter:
    def export_json(self, result: JobResultSchema, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        return output_path

    def export_text(self, content: str, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")
        return output_path
