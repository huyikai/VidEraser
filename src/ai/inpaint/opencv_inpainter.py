from __future__ import annotations

from pathlib import Path

import cv2

from src.ai.inpaint.base_inpainter import BaseInpainter


class OpenCVInpainter(BaseInpainter):
    name = "opencv"

    def process(
        self,
        frames_dir: Path,
        masks_dir: Path,
        output_dir: Path,
        progress_cb=None,
        cancel_cb=None,
    ) -> int:
        output_dir.mkdir(parents=True, exist_ok=True)
        frame_paths = sorted(frames_dir.glob("frame_*.png"))
        processed = 0
        total = len(frame_paths)
        for frame_path in frame_paths:
            if cancel_cb and cancel_cb():
                break
            mask_path = masks_dir / frame_path.name
            frame = cv2.imread(str(frame_path))
            if frame is None:
                continue

            mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
            if mask is None:
                mask = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                mask.fill(0)

            result = cv2.inpaint(frame, mask, inpaintRadius=3, flags=cv2.INPAINT_TELEA)
            cv2.imwrite(str(output_dir / frame_path.name), result)
            processed += 1
            if progress_cb and total > 0:
                progress_cb(processed, total)
        return processed
