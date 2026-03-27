from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QSpinBox,
    QWidget,
)


class RegionSelector(QGroupBox):
    region_changed = Signal(tuple)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("去除区域 (x, y, w, h)", parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QFormLayout(self)
        row = QHBoxLayout()

        self.x_spin = self._create_spin()
        self.y_spin = self._create_spin()
        self.w_spin = self._create_spin(default=320, minimum=1)
        self.h_spin = self._create_spin(default=96, minimum=1)

        row.addWidget(self.x_spin)
        row.addWidget(self.y_spin)
        row.addWidget(self.w_spin)
        row.addWidget(self.h_spin)
        layout.addRow("x / y / w / h", row)

        self.x_spin.valueChanged.connect(self._emit_changed)
        self.y_spin.valueChanged.connect(self._emit_changed)
        self.w_spin.valueChanged.connect(self._emit_changed)
        self.h_spin.valueChanged.connect(self._emit_changed)

    @staticmethod
    def _create_spin(default: int = 0, minimum: int = 0, maximum: int = 10000) -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(minimum, maximum)
        spin.setValue(default)
        spin.setSingleStep(4)
        spin.setFixedWidth(90)
        return spin

    def set_frame_size(self, width: int, height: int) -> None:
        max_w = max(1, width)
        max_h = max(1, height)
        self.x_spin.setRange(0, max_w - 1)
        self.y_spin.setRange(0, max_h - 1)
        self.w_spin.setRange(1, max_w)
        self.h_spin.setRange(1, max_h)
        self.w_spin.setValue(min(self.w_spin.value(), max_w))
        self.h_spin.setValue(min(self.h_spin.value(), max_h))
        self._emit_changed()

    def get_region(self) -> tuple[int, int, int, int]:
        return (
            self.x_spin.value(),
            self.y_spin.value(),
            self.w_spin.value(),
            self.h_spin.value(),
        )

    def _emit_changed(self) -> None:
        self.region_changed.emit(self.get_region())
