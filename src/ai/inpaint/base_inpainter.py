from abc import ABC, abstractmethod
from pathlib import Path


class BaseInpainter(ABC):
    name: str

    @abstractmethod
    def inpaint_segment(self, frames_dir: Path, masks_dir: Path, output_dir: Path) -> Path:
        raise NotImplementedError
