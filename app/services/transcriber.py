from __future__ import annotations

from pathlib import Path

from app.core.config import Settings


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

    def transcribe(self, audio_path: Path) -> tuple[str, str]:
        model = self._load_model()
        result = model.transcribe(str(audio_path))
        return result.get("text", "").strip(), result.get("language", "zh")
