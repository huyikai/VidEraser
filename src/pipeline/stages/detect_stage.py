from __future__ import annotations

from pathlib import Path

from src.ai.detect.paddleocr_detector import PaddleOCRDetector, PaddleOCRNotAvailableError
from PIL import Image

from src.core.config.constants import (
    OCR_REGION_MAX_HEIGHT_FRAC,
    OCR_REGION_MAX_WIDTH_FRAC,
    OCR_SAMPLE_MAX_FRAMES,
)
from src.video.ffmpeg_probe import probe_video


def _default_top_region(input_path: Path) -> tuple[int, int, int, int] | None:
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


def _union_xywh(
    boxes: list[tuple[int, int, int, int]],
) -> tuple[int, int, int, int]:
    x0 = min(x for x, _, _, _ in boxes)
    y0 = min(y for _, y, _, _ in boxes)
    x1 = max(x + w for x, y, w, h in boxes)
    y1 = max(y + h for x, y, w, h in boxes)
    return (x0, y0, max(1, x1 - x0), max(1, y1 - y0))


def _clamp_region_xywh(
    x: int,
    y: int,
    w: int,
    h: int,
    frame_w: int,
    frame_h: int,
) -> tuple[tuple[int, int, int, int], bool]:
    """Cap OCR union to max width/height fraction of frame; keep roughly centered."""
    max_w = min(frame_w, max(1, int(frame_w * OCR_REGION_MAX_WIDTH_FRAC)))
    max_h = min(frame_h, max(1, int(frame_h * OCR_REGION_MAX_HEIGHT_FRAC)))
    if w <= max_w and h <= max_h:
        return (x, y, w, h), False

    new_w = min(w, max_w)
    new_h = min(h, max_h)
    cx = x + w // 2
    cy = y + h // 2
    new_x = max(0, min(frame_w - new_w, cx - new_w // 2))
    new_y = max(0, min(frame_h - new_h, cy - new_h // 2))
    return (new_x, new_y, new_w, new_h), True


def _frame_size_from_path(path: Path) -> tuple[int, int] | None:
    try:
        with Image.open(path) as im:
            return im.size
    except OSError:
        return None


def _sample_frame_paths(frames_dir: Path, max_frames: int) -> list[Path]:
    """Evenly pick up to max_frames from sorted frame_*.png (incl. first/last when possible)."""
    paths = sorted(frames_dir.glob("frame_*.png"))
    n = len(paths)
    if n == 0:
        return []
    k = min(max_frames, n)
    if k <= 0:
        return []
    if k == 1:
        return [paths[0]]
    if k == n:
        return paths
    indices: list[int] = []
    for i in range(k):
        idx = int(round(i * (n - 1) / (k - 1)))
        indices.append(idx)
    out: list[Path] = []
    seen: set[int] = set()
    for idx in indices:
        if idx not in seen:
            seen.add(idx)
            out.append(paths[idx])
    return out


class DetectStage:
    name = "detect"

    def __init__(self) -> None:
        self._paddle = PaddleOCRDetector()

    def run(
        self,
        input_path: Path,
        frames_dir: Path,
        selected_region: tuple[int, int, int, int] | None = None,
        use_auto_detect: bool = False,
        ocr_sample_max_frames: int | None = None,
    ) -> tuple[tuple[int, int, int, int] | None, str]:
        """Return (region, detect_source).

        detect_source: manual | ocr_union_* | default_top | default_after_ocr_empty |
        default_after_ocr_error
        """
        if selected_region:
            return selected_region, "manual"

        if use_auto_detect:
            limit = ocr_sample_max_frames or OCR_SAMPLE_MAX_FRAMES
            samples = _sample_frame_paths(frames_dir, limit)
            if not samples:
                region = _default_top_region(input_path)
                return region, "default_after_ocr_empty"

            all_boxes: list[tuple[int, int, int, int]] = []
            try:
                for sample in samples:
                    boxes = self._paddle.detect(sample)
                    all_boxes.extend(boxes)
            except PaddleOCRNotAvailableError:
                region = _default_top_region(input_path)
                return region, "default_after_ocr_error"
            except Exception:
                region = _default_top_region(input_path)
                return region, "default_after_ocr_error"

            if not all_boxes:
                region = _default_top_region(input_path)
                return region, "default_after_ocr_empty"

            union = _union_xywh(all_boxes)
            size = _frame_size_from_path(samples[0])
            if size is None:
                tag = (
                    "ocr_union"
                    if len(samples) == 1
                    else f"ocr_union_{len(samples)}frames"
                )
                return union, tag

            fw, fh = size
            clamped, did_clamp = _clamp_region_xywh(*union, fw, fh)
            base_tag = (
                "ocr_union"
                if len(samples) == 1
                else f"ocr_union_{len(samples)}frames"
            )
            tag = f"{base_tag}_clamped" if did_clamp else base_tag
            return clamped, tag

        region = _default_top_region(input_path)
        return region, "default_top"
