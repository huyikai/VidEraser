from pathlib import Path

from src.ai.detect.base_detector import BaseDetector


class PaddleOCRDetector(BaseDetector):
    name = "paddleocr"

    def detect(self, frame_path: Path) -> list[tuple[int, int, int, int]]:
        raise NotImplementedError("PaddleOCR detection integration will be added in next phase.")
