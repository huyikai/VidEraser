from __future__ import annotations

from pathlib import Path

from src.video.ffmpeg_probe import probe_video


class DetectStage:
    name = "detect"

    def run(
        self, input_path: Path, selected_region: tuple[int, int, int, int] | None = None
    ) -> tuple[int, int, int, int] | None:
        """Return a region for mask generation.

        Current strategy:
        - Use user-selected region when provided.
        - Fallback to a small top-center region as a lightweight default.
        """
        if selected_region:
            return selected_region

        info = probe_video(input_path)
        video_stream = next(
            (s for s in info.get("streams", []) if s.get("codec_type") == "video"),
            {},
        )
        width = int(video_stream.get("width") or 0)
        height = int(video_stream.get("height") or 0)
        if width <= 0 or height <= 0:
            return None

        region_w = max(64, int(width * 0.35))
        region_h = max(32, int(height * 0.12))
        x = max(0, (width - region_w) // 2)
        y = max(0, int(height * 0.02))
        return (x, y, region_w, region_h)
