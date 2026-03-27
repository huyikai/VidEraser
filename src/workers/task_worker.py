from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread

from src.core.models.task import TaskStatus, VideoTask
from src.pipeline.orchestrator import PipelineOrchestrator
from src.video.ffmpeg_paths import FFmpegNotFoundError
from src.video.ffmpeg_probe import probe_video
from src.workers.worker_signals import WorkerSignals


class TaskWorker(QThread):
    def __init__(self, task: VideoTask, cache_root: Path) -> None:
        super().__init__()
        self.task = task
        self.cache_root = cache_root
        self.signals = WorkerSignals()
        self._cancelled = False
        self.orchestrator = PipelineOrchestrator()

    def cancel(self) -> None:
        self._cancelled = True

    def _check_cancel(self) -> bool:
        if self._cancelled:
            self.task.status = TaskStatus.CANCELLED
            self.signals.cancelled.emit(self.task.task_id)
            self.signals.log.emit(self.task.task_id, "info", "Task cancelled by user.")
            return True
        return False

    def run(self) -> None:
        task_id = self.task.task_id
        cache_dir = self.cache_root / task_id
        cache_dir.mkdir(parents=True, exist_ok=True)
        self.task.status = TaskStatus.RUNNING
        try:
            self.signals.log.emit(task_id, "info", "Reading video metadata...")
            info = probe_video(self.task.input_path)
            video_stream = next(
                (s for s in info.get("streams", []) if s.get("codec_type") == "video"),
                {},
            )
            width = video_stream.get("width", "?")
            height = video_stream.get("height", "?")
            duration = info.get("format", {}).get("duration", "?")
            self.signals.log.emit(
                task_id,
                "info",
                f"Video meta: {width}x{height}, duration={duration}s",
            )
            self.signals.progress.emit(task_id, "probe", 10.0, 0)
            if self._check_cancel():
                return

            output_path = self.task.output_dir / f"{self.task.input_path.stem}_processed.mp4"
            output_path.parent.mkdir(parents=True, exist_ok=True)

            self.signals.log.emit(task_id, "info", "Running full pipeline...")
            self.signals.progress.emit(task_id, "decode", 25.0, 0)
            metrics = self.orchestrator.run_full_pipeline(
                input_path=self.task.input_path,
                cache_dir=cache_dir,
                output_path=output_path,
                selected_region=self.task.selected_region,
                fps=2,
            )
            self.signals.progress.emit(task_id, "inpaint", 80.0, 0)

            frame_count = int(metrics.get("frames_extracted", 0))
            self.signals.log.emit(task_id, "info", f"Decode finished: {frame_count} frames")
            preview_frame = next((cache_dir / "frames").glob("frame_*.png"), None)
            if preview_frame:
                self.signals.preview.emit(task_id, str(preview_frame))

            self.task.status = TaskStatus.DONE
            self.signals.progress.emit(task_id, "complete", 100.0, 0)
            self.signals.done.emit(
                task_id,
                str(output_path),
                {"streams": len(info.get("streams", [])), **metrics},
            )
        except FFmpegNotFoundError as exc:
            self.task.status = TaskStatus.FAILED
            self.signals.error.emit(task_id, "FFMPEG_NOT_FOUND", str(exc), "")
        except Exception as exc:  # noqa: BLE001
            self.task.status = TaskStatus.FAILED
            self.signals.error.emit(task_id, "TASK_FAILED", str(exc), repr(exc))
