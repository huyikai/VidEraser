from pathlib import Path

import ffmpeg

from src.video.ffmpeg_paths import resolve_ffmpeg

def mux_audio(video_path: Path, audio_source: Path, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg_bin = resolve_ffmpeg()
    video_input = ffmpeg.input(str(video_path))
    audio_input = ffmpeg.input(str(audio_source))
    (
        ffmpeg.output(
            video_input.video,
            audio_input.audio,
            str(output_path),
            vcodec="copy",
            acodec="aac",
            shortest=None,
        )
        .overwrite_output()
        .run(quiet=True, cmd=ffmpeg_bin)
    )
    return output_path
