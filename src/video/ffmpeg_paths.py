"""Resolve ffmpeg / ffprobe binaries (PATH, env, common install dirs, bundled third_party)."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from src.utils.paths import project_root


def _ffmpeg_bundle_subdir() -> str:
    if sys.platform == "darwin":
        return "mac"
    if sys.platform.startswith("linux"):
        return "linux"
    if os.name == "nt":
        return "win"
    return "mac"


class FFmpegNotFoundError(RuntimeError):
    """Raised when ffmpeg or ffprobe cannot be located."""

    @staticmethod
    def install_hint() -> str:
        if sys.platform == "darwin":
            return "请安装 FFmpeg（例如：brew install ffmpeg），或设置环境变量 VIDERASER_FFPROBE / VIDERASER_FFMPEG 指向可执行文件。"
        if os.name == "nt":
            return "请安装 FFmpeg 并加入 PATH，或设置环境变量 VIDERASER_FFPROBE / VIDERASER_FFMPEG。"
        return "请安装 FFmpeg 并加入 PATH，或设置环境变量 VIDERASER_FFPROBE / VIDERASER_FFMPEG。"


def _candidates(name: str, bundled_subdir: str) -> list[Path]:
    exe = f"{name}.exe" if os.name == "nt" else name
    root = project_root()

    paths: list[Path] = []

    env_key = "VIDERASER_FFPROBE" if name == "ffprobe" else "VIDERASER_FFMPEG"
    env_val = os.environ.get(env_key, "").strip()
    if env_val:
        paths.append(Path(env_val))

    if name == "ffprobe":
        alt = os.environ.get("FFPROBE_PATH", "").strip()
        if alt:
            paths.append(Path(alt))
    else:
        alt = os.environ.get("FFMPEG_PATH", "").strip()
        if alt:
            paths.append(Path(alt))

    which = shutil.which(name)
    if which:
        paths.append(Path(which))

    if sys.platform == "darwin":
        for base in ("/opt/homebrew/bin", "/usr/local/bin"):
            paths.append(Path(base) / name)
    elif os.name == "nt":
        for base in (os.environ.get("ProgramFiles", ""), os.environ.get("ProgramFiles(x86)", "")):
            if base:
                paths.append(Path(base) / "ffmpeg" / "bin" / exe)

    bundled = root / "third_party" / "ffmpeg" / bundled_subdir / exe
    paths.append(bundled)

    seen: set[str] = set()
    unique: list[Path] = []
    for p in paths:
        key = str(p.resolve()) if p.exists() else str(p)
        if key in seen:
            continue
        seen.add(key)
        unique.append(p)
    return unique


def resolve_ffprobe() -> str:
    for p in _candidates("ffprobe", _ffmpeg_bundle_subdir()):
        if p.is_file() and os.access(p, os.X_OK):
            return str(p)
        if os.name == "nt" and p.is_file():
            return str(p)
    raise FFmpegNotFoundError(
        f"未找到 ffprobe。{FFmpegNotFoundError.install_hint()}"
    )


def resolve_ffmpeg() -> str:
    for p in _candidates("ffmpeg", _ffmpeg_bundle_subdir()):
        if p.is_file() and os.access(p, os.X_OK):
            return str(p)
        if os.name == "nt" and p.is_file():
            return str(p)
    raise FFmpegNotFoundError(
        f"未找到 ffmpeg。{FFmpegNotFoundError.install_hint()}"
    )
