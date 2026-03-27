from pathlib import Path


class WeightsManager:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def has_weights(self, model_name: str) -> bool:
        return (self.root / model_name).exists()
