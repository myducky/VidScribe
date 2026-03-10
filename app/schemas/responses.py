from pydantic import BaseModel

from app.core.enums import ArtifactCleanupTarget
from app.schemas.common import JobResultSchema, JobStatusResponse


class HealthResponse(BaseModel):
    status: str
    app: str


class CreateJobResponse(BaseModel):
    job_id: str
    status: str


class AnalyzeTextResponse(JobResultSchema):
    pass


class AnalyzeVideoResponse(JobResultSchema):
    pass


class AnalyzeRemoteVideoResponse(JobResultSchema):
    pass


class JobDetailResponse(JobStatusResponse):
    pass


class DouyinProbeResponse(BaseModel):
    input_url: str
    normalized_url: str
    downloadable: bool
    reason_code: str
    detail: str
    resolved_video_id: str | None = None


class VideoProbeResponse(BaseModel):
    platform: str
    input_url: str
    normalized_url: str
    downloadable: bool
    reason_code: str
    detail: str
    resolved_video_id: str | None = None


class JobArtifactsCleanupResponse(BaseModel):
    job_id: str
    target: ArtifactCleanupTarget
    deleted_paths: list[str]
    missing_paths: list[str]


class JobArtifactsLocationResponse(BaseModel):
    job_id: str
    job_dir: str
    job_dir_url: str
    downloads_dir: str
    audio_dir: str
    result_json_path: str
    transcript_clean_path: str
    article_html_path: str
    job_dir_exists: bool
    downloads_dir_exists: bool
    audio_dir_exists: bool
    result_json_exists: bool
    transcript_clean_exists: bool
    article_html_exists: bool
