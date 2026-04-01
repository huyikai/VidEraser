from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional
from uuid import uuid4

from src.core.config.constants import INPAINT_BACKEND_OPENCV


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    CANCELLED = "cancelled"
    FAILED = "failed"
    DONE = "done"


@dataclass
class VideoTask:
    input_path: Path
    output_dir: Path
    task_id: str = field(default_factory=lambda: str(uuid4()))
    status: TaskStatus = TaskStatus.PENDING
    selected_region: Optional[tuple[int, int, int, int]] = None
    use_auto_detect: bool = False
    inpaint_backend: str = INPAINT_BACKEND_OPENCV
    # 可选：覆盖默认处理 FPS 上限（PROCESSING_FPS_CAP）
    processing_fps_cap: float | None = None
    # 可选：覆盖 OCR 采样帧数上限（OCR_SAMPLE_MAX_FRAMES）
    ocr_sample_max_frames: int | None = None
