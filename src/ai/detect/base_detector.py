from abc import ABC, abstractmethod
from pathlib import Path


class BaseDetector(ABC):
    name: str

    @abstractmethod
    def detect(self, frame_path: Path) -> list[tuple[int, int, int, int]]:
        raise NotImplementedError
