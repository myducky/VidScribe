from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field(default="VidScribe", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    api_prefix: str = Field(default="/v1", alias="API_PREFIX")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    database_url: str = Field(
        default="sqlite+pysqlite:///./vidscribe.db",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    celery_broker_url: str = Field(default="redis://localhost:6379/0", alias="CELERY_BROKER_URL")
    celery_result_backend: str | None = Field(default="redis://localhost:6379/1", alias="CELERY_RESULT_BACKEND")

    openai_base_url: str | None = Field(default=None, alias="OPENAI_BASE_URL")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    openai_timeout_sec: int = Field(default=60, alias="OPENAI_TIMEOUT_SEC")

    whisper_model: str = Field(default="base", alias="WHISPER_MODEL")
    whisper_initial_prompt: str = Field(
        default=(
            "以下音频以中文普通话口播为主，常见于短视频、电商、品牌、消费和财经语境。"
            "请优先准确识别专有名词、品牌名、平台名、产品名和数字表达，"
            "使用自然的简体中文输出，并补充必要标点。"
            "遇到同音词时，优先选择最常见、最符合上下文的正确词形。"
            "例如“抖音”“星巴克”“瑞幸”“小红书”“直播间”“GMV”。"
        ),
        alias="WHISPER_INITIAL_PROMPT",
    )
    storage_dir: str = Field(default="storage", alias="STORAGE_DIR")
    max_upload_mb: int = Field(default=300, alias="MAX_UPLOAD_MB")
    video_download_socket_timeout_sec: int = Field(default=20, alias="VIDEO_DOWNLOAD_SOCKET_TIMEOUT_SEC")
    video_download_retries: int = Field(default=2, alias="VIDEO_DOWNLOAD_RETRIES")
    video_download_force_ipv4: bool = Field(default=True, alias="VIDEO_DOWNLOAD_FORCE_IPV4")
    douyin_cookie_file: str | None = Field(default=None, alias="DOUYIN_COOKIE_FILE")
    douyin_cookies_from_browser: str | None = Field(default=None, alias="DOUYIN_COOKIES_FROM_BROWSER")
    writing_style_file: str = Field(default="app/prompts/writing_style.md", alias="WRITING_STYLE_FILE")

    @property
    def storage_path(self) -> Path:
        path = Path(self.storage_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def writing_style_path(self) -> Path:
        return Path(self.writing_style_file)


@lru_cache
def get_settings() -> Settings:
    return Settings()
