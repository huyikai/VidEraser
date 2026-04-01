from __future__ import annotations

from pathlib import Path

import time
from PySide6.QtCore import QThread

from src.core.config.constants import (
    OCR_SAMPLE_MAX_FRAMES,
    PIPELINE_FPS_CAP,
    PIPELINE_FPS_MIN,
    PROCESSING_FPS_CAP,
)
from src.core.models.task import TaskStatus, VideoTask
from src.pipeline.orchestrator import PipelineOrchestrator
from src.video.ffmpeg_paths import FFmpegNotFoundError
from src.video.ffmpeg_probe import probe_video, video_fps_from_probe_info
from src.utils.validators import normalize_inpaint_backend
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
            # 避免多次触发 cancelled 信号/日志
            if self.task.status != TaskStatus.CANCELLED:
                self.task.status = TaskStatus.CANCELLED
                self.signals.cancelled.emit(self.task.task_id)
                self.signals.log.emit(
                    self.task.task_id,
                    "info",
                    "Task cancelled by user.",
                )
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
            src_fps = video_fps_from_probe_info(info)
            # 允许任务级覆盖处理 FPS 上限
            processing_cap = (
                float(self.task.processing_fps_cap)
                if getattr(self.task, "processing_fps_cap", None)
                not in (None, 0)
                else PROCESSING_FPS_CAP
            )
            pipeline_fps = max(
                PIPELINE_FPS_MIN,
                min(PIPELINE_FPS_CAP, src_fps, processing_cap),
            )
            self.signals.log.emit(
                task_id,
                "info",
                f"管线帧率: 源≈{src_fps:.3f} fps，处理上限 {processing_cap:.0f} fps → 使用 {pipeline_fps:.3f} fps（解码/编码一致）",
            )
            self.signals.log.emit(
                task_id,
                "info",
                f"OCR 采样上限: {getattr(self.task, 'ocr_sample_max_frames', None) or OCR_SAMPLE_MAX_FRAMES} 帧",
            )
            self.signals.progress.emit(task_id, "probe", 10.0, 0)
            if self._check_cancel():
                return

            output_path = self.task.output_dir / f"{self.task.input_path.stem}_processed.mp4"
            output_path.parent.mkdir(parents=True, exist_ok=True)

            if self.task.use_auto_detect:
                self.signals.log.emit(
                    task_id,
                    "info",
                    "区域模式: PaddleOCR 自动检测（多帧均匀采样合并框，失败则回退顶区）",
                )
            else:
                self.signals.log.emit(
                    task_id,
                    "info",
                    f"区域模式: 手动框选 {self.task.selected_region}",
                )

            inpaint_backend = normalize_inpaint_backend(self.task.inpaint_backend)
            self.signals.log.emit(
                task_id,
                "info",
                f"修复模型: {inpaint_backend}",
            )

            self.signals.log.emit(task_id, "info", "Running full pipeline...")
            self.signals.progress.emit(task_id, "decode", 25.0, 0)
            region_arg = None if self.task.use_auto_detect else self.task.selected_region

            inpaint_started_at: float | None = None
            last_inpaint_percent: float = 25.0

            def inpaint_cancel_cb() -> bool:
                # 在 inpaint 循环中“每帧前”检查取消；返回 True 表示应中断。
                return self._check_cancel()

            def inpaint_progress_cb(processed: int, total: int) -> None:
                nonlocal inpaint_started_at, last_inpaint_percent
                if total <= 0:
                    percent = 80.0
                    eta = 0
                else:
                    percent = 25.0 + (processed / total) * 55.0
                    percent = max(0.0, min(80.0, float(percent)))

                    if inpaint_started_at is None:
                        inpaint_started_at = time.monotonic()
                    elapsed = max(0.0, time.monotonic() - inpaint_started_at)

                    eta = 0
                    if processed > 0:
                        avg_per_frame = elapsed / processed
                        eta_frames = max(0, total - processed)
                        eta = int(avg_per_frame * eta_frames)

                last_inpaint_percent = percent
                self.signals.progress.emit(task_id, "inpaint", percent, eta)

            metrics = self.orchestrator.run_full_pipeline(
                input_path=self.task.input_path,
                cache_dir=cache_dir,
                output_path=output_path,
                selected_region=region_arg,
                use_auto_detect=self.task.use_auto_detect,
                inpaint_backend=inpaint_backend,
                inpaint_progress_cb=inpaint_progress_cb,
                inpaint_cancel_cb=inpaint_cancel_cb,
                ocr_sample_max_frames=getattr(self.task, "ocr_sample_max_frames", None),
                fps=pipeline_fps,
            )

            if self.task.status == TaskStatus.CANCELLED or self._cancelled:
                return

            # 若 inpaint 阶段没有触发逐帧回调（例如 total=0），至少补一次到 80%
            if last_inpaint_percent < 80.0 and not self._cancelled:
                self.signals.progress.emit(task_id, "inpaint", 80.0, 0)

            frame_count = int(metrics.get("frames_extracted", 0))
            detect_src = metrics.get("detect_source", "")
            self.signals.log.emit(
                task_id,
                "info",
                f"Decode finished: {frame_count} frames; detect={detect_src}",
            )
            preview_frame = next((cache_dir / "frames").glob("frame_*.png"), None)
            if preview_frame:
                self.signals.preview.emit(task_id, str(preview_frame))

            if self.task.status == TaskStatus.CANCELLED or self._cancelled:
                return

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
