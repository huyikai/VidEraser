import json
import subprocess
from pathlib import Path
from typing import Any

from src.video.ffmpeg_paths import resolve_ffprobe


class FFmpegProbeError(RuntimeError):
    pass


def probe_video(input_path: Path) -> dict[str, Any]:
    ffprobe_bin = resolve_ffprobe()
    command = [
        ffprobe_bin,
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(input_path),
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except Exception as exc:  # noqa: BLE001
        raise FFmpegProbeError(f"ffprobe failed: {exc}") from exc
