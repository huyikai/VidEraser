from pathlib import Path

from src.video.frame_extractor import extract_frames


class DecodeStage:
    name = "decode"

    def run(self, input_path: Path, cache_dir: Path, fps: int = 2) -> int:
        frames_dir = cache_dir / "frames"
        return extract_frames(input_path=input_path, output_dir=frames_dir, fps=fps)
