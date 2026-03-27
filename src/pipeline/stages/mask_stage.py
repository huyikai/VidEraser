from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw


class MaskStage:
    name = "mask"

    def run(
        self,
        frames_dir: Path,
        masks_dir: Path,
        region: tuple[int, int, int, int] | None,
    ) -> int:
        masks_dir.mkdir(parents=True, exist_ok=True)
        frame_paths = sorted(frames_dir.glob("frame_*.png"))
        if not frame_paths:
            return 0

        for frame_path in frame_paths:
            with Image.open(frame_path) as img:
                width, height = img.size
                mask = Image.new("L", (width, height), color=0)
                if region:
                    x, y, w, h = region
                    x2 = min(width, x + w)
                    y2 = min(height, y + h)
                    if x < x2 and y < y2:
                        draw = ImageDraw.Draw(mask)
                        draw.rectangle([x, y, x2, y2], fill=255)
                mask.save(masks_dir / frame_path.name)
        return len(frame_paths)
