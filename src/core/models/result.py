from dataclasses import dataclass
from pathlib import Path


@dataclass
class TaskResult:
    task_id: str
    output_path: Path
    message: str = "Task completed"
