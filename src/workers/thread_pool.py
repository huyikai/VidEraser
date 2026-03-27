from PySide6.QtCore import QThreadPool


def get_thread_pool() -> QThreadPool:
    return QThreadPool.globalInstance()
