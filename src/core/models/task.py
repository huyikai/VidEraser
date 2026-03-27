from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional
from uuid import uuid4


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
