from abc import ABC, abstractmethod
from collections.abc import Callable
from pathlib import Path
from typing import Optional


class BaseInpainter(ABC):
    name: str

    @abstractmethod
    def process(
        self,
        frames_dir: Path,
        masks_dir: Path,
        output_dir: Path,
        progress_cb: Optional[Callable[[int, int], None]] = None,
        cancel_cb: Optional[Callable[[], bool]] = None,
    ) -> int:
        """Write inpainted frames to output_dir; return count processed.

        progress_cb: called as progress_cb(processed, total) after each frame (best effort).
        cancel_cb: called before each frame (best effort); if it returns True, should stop early.
        """
