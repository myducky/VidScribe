from pathlib import Path
from uuid import uuid4


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_upload_suffix(filename: str | None, *, default: str = ".mp4") -> str:
    suffix = Path(filename or "").suffix.lower()
    if not suffix:
        return default
    if not suffix.startswith("."):
        return default
    if not suffix[1:].isalnum():
        return default
    return suffix


def generate_upload_filename(filename: str | None, *, default_suffix: str = ".mp4") -> str:
    return f"{uuid4().hex}{safe_upload_suffix(filename, default=default_suffix)}"


def resolve_upload_reference(upload_dir: Path, reference: str) -> Path:
    candidate = upload_dir / Path(reference).name
    resolved_upload_dir = upload_dir.resolve()
    resolved_candidate = candidate.resolve()
    if resolved_candidate.parent != resolved_upload_dir:
        raise ValueError("uploaded_video_path must reference a file inside storage/uploads")
    return resolved_candidate
