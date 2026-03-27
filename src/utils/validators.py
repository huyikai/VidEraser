from pathlib import Path


def ensure_video_file(path: Path) -> bool:
    return path.exists() and path.suffix.lower() in {".mp4", ".mov", ".mkv", ".avi", ".flv", ".webm"}
