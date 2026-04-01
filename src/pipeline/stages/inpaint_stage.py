from __future__ import annotations

from pathlib import Path

from src.ai.inpaint.lama_inpainter import LaMaInpainter
from src.ai.inpaint.opencv_inpainter import OpenCVInpainter
from src.ai.inpaint.propainter_inpainter import ProPainterInpainter
from src.core.config.constants import (
    INPAINT_BACKEND_LAMA,
    INPAINT_BACKEND_OPENCV,
    INPAINT_BACKEND_PROPAINTER,
)


class InpaintStage:
    name = "inpaint"

    def __init__(self) -> None:
        self._opencv = OpenCVInpainter()
        self._lama = LaMaInpainter()
        self._propainter = ProPainterInpainter()

    def run(
        self,
        frames_dir: Path,
        masks_dir: Path,
        output_dir: Path,
        backend: str = INPAINT_BACKEND_OPENCV,
        progress_cb=None,
        cancel_cb=None,
    ) -> int:
        b = backend.strip().lower()
        if b == INPAINT_BACKEND_LAMA:
            return self._lama.process(
                frames_dir,
                masks_dir,
                output_dir,
                progress_cb=progress_cb,
                cancel_cb=cancel_cb,
            )
        if b == INPAINT_BACKEND_PROPAINTER:
            return self._propainter.process(
                frames_dir,
                masks_dir,
                output_dir,
                progress_cb=progress_cb,
                cancel_cb=cancel_cb,
            )
        return self._opencv.process(
            frames_dir,
            masks_dir,
            output_dir,
            progress_cb=progress_cb,
            cancel_cb=cancel_cb,
        )
