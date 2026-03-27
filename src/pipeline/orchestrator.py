from pathlib import Path

from src.pipeline.stages.detect_stage import DetectStage
from src.pipeline.stages.decode_stage import DecodeStage
from src.pipeline.stages.encode_stage import EncodeStage
from src.pipeline.stages.inpaint_stage import InpaintStage
from src.pipeline.stages.mask_stage import MaskStage


class PipelineOrchestrator:
    def __init__(self) -> None:
        self.decode_stage = DecodeStage()
        self.detect_stage = DetectStage()
        self.mask_stage = MaskStage()
        self.inpaint_stage = InpaintStage()
        self.encode_stage = EncodeStage()

    def run_decode_only(self, input_path: Path, cache_dir: Path, fps: int = 2) -> int:
        return self.decode_stage.run(input_path=input_path, cache_dir=cache_dir, fps=fps)

    def run_full_pipeline(
        self,
        input_path: Path,
        cache_dir: Path,
        output_path: Path,
        selected_region: tuple[int, int, int, int] | None = None,
        fps: int = 2,
    ) -> dict[str, int | str]:
        frames_dir = cache_dir / "frames"
        masks_dir = cache_dir / "masks"
        inpainted_dir = cache_dir / "inpainted"

        frame_count = self.decode_stage.run(input_path=input_path, cache_dir=cache_dir, fps=fps)
        region = self.detect_stage.run(input_path=input_path, selected_region=selected_region)
        mask_count = self.mask_stage.run(frames_dir=frames_dir, masks_dir=masks_dir, region=region)
        inpaint_count = self.inpaint_stage.run(
            frames_dir=frames_dir,
            masks_dir=masks_dir,
            output_dir=inpainted_dir,
        )
        final_output = self.encode_stage.run(
            inpainted_frames_dir=inpainted_dir,
            input_video_path=input_path,
            output_path=output_path,
            fps=fps,
        )
        return {
            "frames_extracted": frame_count,
            "masks_generated": mask_count,
            "frames_inpainted": inpaint_count,
            "output_path": str(final_output),
        }
