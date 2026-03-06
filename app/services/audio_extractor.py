from __future__ import annotations

import subprocess
from pathlib import Path

from app.core.errors import InvalidMediaError


class AudioExtractor:
    def extract(self, video_path: Path, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        audio_path = output_dir / f"{video_path.stem}.mp3"
        command = [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-vn",
            "-acodec",
            "libmp3lame",
            str(audio_path),
        ]
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        if completed.returncode != 0:
            raise InvalidMediaError("Uploaded file is not a valid or supported video.")
        return audio_path
