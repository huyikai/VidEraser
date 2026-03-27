from pathlib import Path

import ffmpeg

from src.video.ffmpeg_paths import resolve_ffmpeg


def extract_frames(input_path: Path, output_dir: Path, fps: int = 2) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_pattern = output_dir / "frame_%06d.png"
    ffmpeg_bin = resolve_ffmpeg()
    (
        ffmpeg.input(str(input_path))
        .filter("fps", fps=fps)
        .output(str(output_pattern), start_number=0)
        .overwrite_output()
        .run(quiet=True, cmd=ffmpeg_bin)
    )
    return len(list(output_dir.glob("frame_*.png")))
