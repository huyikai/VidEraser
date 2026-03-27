from __future__ import annotations

from pathlib import Path

import cv2


class InpaintStage:
    name = "inpaint"

    def run(self, frames_dir: Path, masks_dir: Path, output_dir: Path) -> int:
        output_dir.mkdir(parents=True, exist_ok=True)
        frame_paths = sorted(frames_dir.glob("frame_*.png"))
        if not frame_paths:
            return 0

        processed = 0
        for frame_path in frame_paths:
            mask_path = masks_dir / frame_path.name
            frame = cv2.imread(str(frame_path))
            if frame is None:
                continue

            mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
            if mask is None:
                mask = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                mask.fill(0)

            # A light OpenCV inpaint fallback keeps the pipeline executable
            # before integrating heavy models like LaMa/ProPainter.
            result = cv2.inpaint(frame, mask, inpaintRadius=3, flags=cv2.INPAINT_TELEA)
            cv2.imwrite(str(output_dir / frame_path.name), result)
            processed += 1
        return processed
