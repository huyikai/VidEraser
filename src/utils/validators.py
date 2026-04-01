from pathlib import Path


def ensure_video_file(path: Path) -> bool:
    return path.exists() and path.suffix.lower() in {".mp4", ".mov", ".mkv", ".avi", ".flv", ".webm"}


def normalize_inpaint_backend(value: str) -> str:
    from src.core.config.constants import INPAINT_BACKEND_OPENCV, VALID_INPAINT_BACKENDS

    v = (value or "").strip().lower()
    if v in VALID_INPAINT_BACKENDS:
        return v
    return INPAINT_BACKEND_OPENCV
