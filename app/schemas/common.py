from datetime import datetime

from pydantic import BaseModel, Field

from app.core.enums import InputType, JobStatus, StepStatus


class CoverSchema(BaseModel):
    prompt: str
    layout: str
    text_on_cover: str
    image_prompt_en: str | None = None


class SourceSchema(BaseModel):
    language: str = "zh"
    duration_sec: float = 0
    transcript_raw: str
    transcript_clean: str


class JobResultSchema(BaseModel):
    job_id: str
    input_type: InputType
    status: JobStatus
    title_candidates: list[str] = Field(default_factory=list)
    summary: str = ""
    outline: list[str] = Field(default_factory=list)
    highlights: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    article_markdown: str = ""
    cover: CoverSchema
    source: SourceSchema


class JobStepSchema(BaseModel):
    step_name: str
    status: StepStatus
    start_time: datetime | None = None
    end_time: datetime | None = None
    error_message: str | None = None
    retry_count: int = 0


class JobStatusResponse(BaseModel):
    job_id: str
    input_type: InputType
    status: JobStatus
    error_message: str | None = None
    steps: list[JobStepSchema] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
