from __future__ import annotations

import os
from pathlib import Path

from app.core.config import Settings
from app.services.audio_extractor import resolve_ffmpeg_executable


class Transcriber:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._model = None

    def _load_model(self):
        if self._model is None:
            import whisper  # type: ignore

            if not hasattr(whisper, "load_model"):
                raise RuntimeError(
                    "The installed 'whisper' package is incompatible. Install 'openai-whisper' to enable transcription."
                )

            self._model = whisper.load_model(self.settings.whisper_model)
        return self._model

    def _ensure_ffmpeg_on_path(self) -> None:
        runtime_bin = self.settings.storage_path / ".runtime-bin"
        runtime_bin.mkdir(parents=True, exist_ok=True)

        ffmpeg_link = runtime_bin / "ffmpeg"
        ffmpeg_target = Path(resolve_ffmpeg_executable())
        if ffmpeg_link.exists() or ffmpeg_link.is_symlink():
            ffmpeg_link.unlink()
        ffmpeg_link.symlink_to(ffmpeg_target)

        current_path = os.environ.get("PATH", "")
        runtime_bin_str = str(runtime_bin)
        if runtime_bin_str not in current_path.split(os.pathsep):
            os.environ["PATH"] = os.pathsep.join(filter(None, [runtime_bin_str, current_path]))

    def transcribe(self, audio_path: Path) -> tuple[str, str]:
        self._ensure_ffmpeg_on_path()
        model = self._load_model()
        result = model.transcribe(str(audio_path))
        return result.get("text", "").strip(), result.get("language", "zh")
