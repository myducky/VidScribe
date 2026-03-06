from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.enums import InputType


class DouyinProbeRequest(BaseModel):
    douyin_url: str = Field(min_length=1, description="Douyin URL to probe before download")


class VideoProbeRequest(BaseModel):
    video_url: str = Field(min_length=1, description="Video URL to probe before download")


class AnalyzeRemoteVideoRequest(BaseModel):
    video_url: str = Field(min_length=1, description="Remote video URL to download and analyze")
    raw_text: str | None = Field(default=None, description="Optional fallback text when remote download fails")
    desired_length: int = Field(default=1200, ge=800, le=1800)
    language: str = "zh"


class CreateJobRequest(BaseModel):
    input_type: InputType
    bilibili_url: str | None = None
    douyin_url: str | None = None
    raw_text: str | None = None
    uploaded_video_path: str | None = None
    desired_length: int = Field(default=1200, ge=800, le=1800)
    language: str = "zh"

    @model_validator(mode="after")
    def validate_payload(self) -> "CreateJobRequest":
        if self.input_type == InputType.RAW_TEXT and not self.raw_text:
            raise ValueError("raw_text is required when input_type=raw_text")
        if self.input_type == InputType.BILIBILI_URL and not self.bilibili_url:
            raise ValueError("bilibili_url is required when input_type=bilibili_url")
        if self.input_type == InputType.DOUYIN_URL and not self.douyin_url:
            raise ValueError("douyin_url is required when input_type=douyin_url")
        if self.input_type == InputType.UPLOADED_VIDEO and not self.uploaded_video_path:
            raise ValueError("uploaded_video_path is required when input_type=uploaded_video")
        return self


class AnalyzeTextRequest(BaseModel):
    raw_text: str = Field(min_length=20, description="Transcript, caption, or pasted text")
    desired_length: int = Field(default=1200, ge=800, le=1800)
    language: str = "zh"

    model_config = ConfigDict(json_schema_extra={"example": {"raw_text": "这里是一段待处理文案", "desired_length": 1200}})
