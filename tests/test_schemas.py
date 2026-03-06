import pytest
from pydantic import ValidationError

from app.schemas.requests import AnalyzeTextRequest, CreateJobRequest


def test_analyze_text_request_validation():
    request = AnalyzeTextRequest(raw_text="a" * 30, desired_length=1200, language="zh")
    assert request.desired_length == 1200


def test_create_job_request_requires_raw_text():
    with pytest.raises(ValidationError):
        CreateJobRequest(input_type="raw_text")


def test_create_job_request_requires_bilibili_url():
    with pytest.raises(ValidationError):
        CreateJobRequest(input_type="bilibili_url")
