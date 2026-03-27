import subprocess


def run_ffmpeg(command: list[str]) -> int:
    return subprocess.run(command, check=False).returncode
