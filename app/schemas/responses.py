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


class JobDetailResponse(JobStatusResponse):
    pass
