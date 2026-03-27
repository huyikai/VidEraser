from PySide6.QtCore import QObject, Signal


class WorkerSignals(QObject):
    progress = Signal(str, str, float, int)
    preview = Signal(str, str)
    log = Signal(str, str, str)
    error = Signal(str, str, str, str)
    done = Signal(str, str, dict)
    cancelled = Signal(str)
