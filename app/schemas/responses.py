from pydantic import BaseModel

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
