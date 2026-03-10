from __future__ import annotations

import subprocess
from functools import lru_cache
from pathlib import Path
from shutil import which

from app.core.errors import InvalidMediaError


@lru_cache
def resolve_ffmpeg_executable() -> str:
    try:
        import imageio_ffmpeg
    except ImportError:
        imageio_ffmpeg = None

    if imageio_ffmpeg is not None:
        return imageio_ffmpeg.get_ffmpeg_exe()

    ffmpeg_path = which("ffmpeg")
    if ffmpeg_path:
        return ffmpeg_path

    raise InvalidMediaError(
        "FFmpeg is unavailable. Install FFmpeg or ensure the bundled binary can be resolved."
    )


class AudioExtractor:
    def extract(self, video_path: Path, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        audio_path = output_dir / f"{video_path.stem}.mp3"
        command = [
            resolve_ffmpeg_executable(),
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
