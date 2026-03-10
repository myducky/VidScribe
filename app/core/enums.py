from enum import Enum


class InputType(str, Enum):
    BILIBILI_URL = "bilibili_url"
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


class ArtifactCleanupTarget(str, Enum):
    MEDIA = "media"
    ALL = "all"
