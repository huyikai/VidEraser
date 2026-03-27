from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def cache_root() -> Path:
    path = project_root() / ".cache"
    path.mkdir(parents=True, exist_ok=True)
    return path


def output_root() -> Path:
    path = project_root() / "output"
    path.mkdir(parents=True, exist_ok=True)
    return path
