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


def parse_avg_frame_rate(avg_frame_rate: str | None) -> float | None:
    """Parse ffprobe avg_frame_rate like 24000/1001 to float fps."""
    if not avg_frame_rate:
        return None
    s = str(avg_frame_rate).strip()
    if "/" in s:
        num_s, den_s = s.split("/", 1)
        try:
            num = float(num_s)
            den = float(den_s)
            if den == 0:
                return None
            return num / den
        except ValueError:
            return None
    try:
        return float(s)
    except ValueError:
        return None


def video_fps_from_probe_info(info: dict[str, Any]) -> float:
    """Return positive fps from probe json; fallback if missing."""
    from src.core.config.constants import PIPELINE_FPS_FALLBACK

    stream = next(
        (s for s in info.get("streams", []) if s.get("codec_type") == "video"),
        {},
    )
    fps = parse_avg_frame_rate(stream.get("avg_frame_rate"))
    if fps is None or fps <= 0:
        return PIPELINE_FPS_FALLBACK
    return fps
