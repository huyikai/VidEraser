from __future__ import annotations

from pathlib import Path

from src.video.audio_muxer import mux_audio
from src.video.frame_assembler import assemble_video


class EncodeStage:
    name = "encode"

    def run(
        self,
        inpainted_frames_dir: Path,
        input_video_path: Path,
        output_path: Path,
        fps: float = 30.0,
    ) -> Path:
        tmp_video = output_path.with_name(f"{output_path.stem}_silent.mp4")
        assemble_video(inpainted_frames_dir, tmp_video, fps=fps)
        mux_audio(tmp_video, input_video_path, output_path)
        if tmp_video.exists():
            tmp_video.unlink()
        return output_path
