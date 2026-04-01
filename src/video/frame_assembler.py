from pathlib import Path

import ffmpeg

from src.video.ffmpeg_paths import resolve_ffmpeg


def assemble_video(frames_dir: Path, output_path: Path, fps: float = 30.0) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg_bin = resolve_ffmpeg()
    input_pattern = frames_dir / "frame_%06d.png"
    (
        ffmpeg.input(str(input_pattern), framerate=fps)
        .output(str(output_path), vcodec="libx264", pix_fmt="yuv420p", an=None)
        .overwrite_output()
        .run(quiet=True, cmd=ffmpeg_bin)
    )
    return output_path
