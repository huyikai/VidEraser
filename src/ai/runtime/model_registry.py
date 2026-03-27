class ModelRegistry:
    def __init__(self) -> None:
        self._registry: dict[str, str] = {}

    def register(self, name: str, path: str) -> None:
        self._registry[name] = path

    def get(self, name: str) -> str | None:
        return self._registry.get(name)
