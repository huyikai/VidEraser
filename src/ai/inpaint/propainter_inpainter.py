from pathlib import Path

from src.ai.inpaint.base_inpainter import BaseInpainter


class ProPainterInpainter(BaseInpainter):
    name = "propainter"

    def inpaint_segment(self, frames_dir: Path, masks_dir: Path, output_dir: Path) -> Path:
        raise NotImplementedError("ProPainter integration will be added in next phase.")
