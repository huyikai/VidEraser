from pathlib import Path

from src.pipeline.stages.decode_stage import DecodeStage


class PipelineOrchestrator:
    def __init__(self) -> None:
        self.decode_stage = DecodeStage()

    def run_decode_only(self, input_path: Path, cache_dir: Path, fps: int = 2) -> int:
        return self.decode_stage.run(input_path=input_path, cache_dir=cache_dir, fps=fps)
