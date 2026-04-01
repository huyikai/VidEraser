from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from src.ai.detect.base_detector import BaseDetector


class PaddleOCRNotAvailableError(RuntimeError):
    """Raised when paddlepaddle or paddleocr cannot be used."""


def _quad_to_xywh(quad: np.ndarray) -> tuple[int, int, int, int]:
    xs = quad[:, 0]
    ys = quad[:, 1]
    x0 = int(np.floor(xs.min()))
    y0 = int(np.floor(ys.min()))
    x1 = int(np.ceil(xs.max()))
    y1 = int(np.ceil(ys.max()))
    return (x0, y0, max(1, x1 - x0), max(1, y1 - y0))


def _collect_quads(item: Any, out: list[np.ndarray], depth: int = 0) -> None:
    if depth > 16:
        return
    if isinstance(item, dict):
        for key in ("dt_polys", "rec_polys", "dt_boxes", "rec_boxes", "boxes", "polys"):
            if key in item:
                _collect_quads(item[key], out, depth + 1)
        return
    if isinstance(item, np.ndarray):
        if item.ndim == 2 and item.shape[0] == 4 and item.shape[1] == 2:
            out.append(item.astype(np.float32))
        return
    if isinstance(item, (list, tuple)):
        if len(item) == 4:
            try:
                arr = np.array(item, dtype=np.float32)
                if arr.shape == (4, 2):
                    out.append(arr)
                    return
            except (ValueError, TypeError):
                pass
        for sub in item:
            _collect_quads(sub, out, depth + 1)
        return
    j = getattr(item, "json", None)
    if j is not None and not isinstance(item, (dict, list, tuple, np.ndarray)):
        try:
            payload = j() if callable(j) else j
        except TypeError:
            payload = j
        if payload is not None:
            _collect_quads(payload, out, depth + 1)
            return
    if hasattr(item, "__dict__") and not isinstance(item, type):
        _collect_quads(vars(item), out, depth + 1)


class PaddleOCRDetector(BaseDetector):
    name = "paddleocr"

    def __init__(self, lang: str = "ch") -> None:
        self._lang = lang
        self._ocr: Any = None

    def _ensure_engine(self) -> None:
        if self._ocr is not None:
            return
        try:
            import paddle  # noqa: F401
        except ImportError as exc:
            raise PaddleOCRNotAvailableError(
                "未安装 paddlepaddle，无法使用自动检测。请执行: pip install paddlepaddle"
            ) from exc
        try:
            from paddleocr import PaddleOCR
        except ImportError as exc:
            raise PaddleOCRNotAvailableError(
                "未安装 paddleocr。请执行: pip install paddleocr"
            ) from exc

        self._ocr = PaddleOCR(
            lang=self._lang,
            use_textline_orientation=False,
        )

    def detect(self, frame_path: Path) -> list[tuple[int, int, int, int]]:
        if not frame_path.is_file():
            return []
        self._ensure_engine()
        raw = self._ocr.predict(str(frame_path))
        quads: list[np.ndarray] = []
        _collect_quads(raw, quads)
        return [_quad_to_xywh(q) for q in quads]
