from pathlib import Path

from app.core.enums import InputType


class InputResolver:
    def resolve(
        self,
        input_type: InputType,
        *,
        raw_text: str | None = None,
        bilibili_url: str | None = None,
        douyin_url: str | None = None,
        file_path: Path | None = None,
    ) -> dict:
        if input_type == InputType.RAW_TEXT:
            if not raw_text:
                raise ValueError("raw_text is required")
            return {"input_type": input_type.value, "raw_text": raw_text}

        if input_type == InputType.BILIBILI_URL:
            if not bilibili_url:
                raise ValueError("bilibili_url is required")
            return {"input_type": input_type.value, "bilibili_url": bilibili_url}

        if input_type == InputType.DOUYIN_URL:
            if not douyin_url:
                raise ValueError("douyin_url is required")
            return {"input_type": input_type.value, "douyin_url": douyin_url}

        if input_type == InputType.UPLOADED_VIDEO:
            if not file_path:
                raise ValueError("file_path is required")
            return {"input_type": input_type.value, "file_path": str(file_path)}

        raise ValueError(f"Unsupported input type: {input_type}")
