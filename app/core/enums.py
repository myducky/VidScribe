from enum import Enum


class InputType(str, Enum):
    DOUYIN_URL = "douyin_url"
    RAW_TEXT = "raw_text"
    UPLOADED_VIDEO = "uploaded_video"


class JobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class StepStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
