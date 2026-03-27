from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject

from src.core.models.task import VideoTask
from src.workers.task_worker import TaskWorker


class TaskService(QObject):
    def __init__(self, cache_root: Path, output_root: Path) -> None:
        super().__init__()
        self.cache_root = cache_root
        self.output_root = output_root
        self.current_worker: Optional[TaskWorker] = None

    def create_task(self, input_path: Path) -> VideoTask:
        return VideoTask(input_path=input_path, output_dir=self.output_root)

    def start_task(self, task: VideoTask) -> TaskWorker:
        worker = TaskWorker(task=task, cache_root=self.cache_root)
        self.current_worker = worker
        worker.start()
        return worker

    def cancel_current_task(self) -> None:
        if self.current_worker and self.current_worker.isRunning():
            self.current_worker.cancel()
