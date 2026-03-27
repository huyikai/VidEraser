from dataclasses import dataclass


@dataclass
class TaskProgress:
    task_id: str
    stage: str
    percent: float
    eta_seconds: int = 0
