from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QWidget


class VideoPreview(QWidget):
    """等比缩放显示预览图，并在视频坐标系下框选区域 (x, y, w, h)。"""

    region_changed = Signal(int, int, int, int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._pixmap: QPixmap | None = None
        self._native_w = 0
        self._native_h = 0
        self._region: tuple[int, int, int, int] = (0, 0, 1, 1)
        self._has_frame = False
        self._dragging = False
        self._drag_origin = QPoint()
        self._drag_current = QPoint()
        self.setMinimumHeight(200)
        self.setMouseTracking(True)
        self._interactive = True

    def clear(self) -> None:
        self._pixmap = None
        self._native_w = 0
        self._native_h = 0
        self._has_frame = False
        self._dragging = False
        self.update()

    def native_size(self) -> tuple[int, int]:
        return (self._native_w, self._native_h)

    def set_preview_image(self, image: QImage, native_width: int, native_height: int) -> None:
        self._native_w = max(1, native_width)
        self._native_h = max(1, native_height)
        max_side = 960
        img = QImage(image)
        if img.width() > max_side or img.height() > max_side:
            img = img.scaled(
                max_side,
                max_side,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        self._pixmap = QPixmap.fromImage(img)
        self._has_frame = not self._pixmap.isNull()
        self.update()

    def set_region_native(self, x: int, y: int, w: int, h: int) -> None:
        self._region = (x, y, max(1, w), max(1, h))
        self.update()

    def get_region_native(self) -> tuple[int, int, int, int]:
        return self._region

    def set_interactive(self, enabled: bool) -> None:
        self._interactive = enabled
        self._dragging = False
        self.update()

    def _dest_rect(self) -> QRect:
        if not self._pixmap or self._pixmap.isNull():
            return QRect()
        pw = self._pixmap.width()
        ph = self._pixmap.height()
        w, h = self.width(), self.height()
        if w <= 0 or h <= 0 or pw <= 0 or ph <= 0:
            return QRect()
        scale = min(w / pw, h / ph)
        dw = int(pw * scale)
        dh = int(ph * scale)
        dx = (w - dw) // 2
        dy = (h - dh) // 2
        return QRect(dx, dy, dw, dh)

    def _widget_rect_to_native(self, rect: QRect) -> tuple[int, int, int, int]:
        dest = self._dest_rect()
        if dest.isEmpty() or self._native_w <= 0 or self._native_h <= 0:
            return self._region

        x1 = (rect.left() - dest.left()) * self._native_w / dest.width()
        y1 = (rect.top() - dest.top()) * self._native_h / dest.height()
        x2 = (rect.right() - dest.left()) * self._native_w / dest.width()
        y2 = (rect.bottom() - dest.top()) * self._native_h / dest.height()

        nx1 = int(round(min(x1, x2)))
        ny1 = int(round(min(y1, y2)))
        nx2 = int(round(max(x1, x2)))
        ny2 = int(round(max(y1, y2)))

        nx1 = max(0, min(self._native_w - 1, nx1))
        ny1 = max(0, min(self._native_h - 1, ny1))
        nx2 = max(nx1 + 1, min(self._native_w, nx2))
        ny2 = max(ny1 + 1, min(self._native_h, ny2))
        return (nx1, ny1, nx2 - nx1, ny2 - ny1)

    def _native_rect_to_widget(self, x: int, y: int, w: int, h: int) -> QRect:
        dest = self._dest_rect()
        if dest.isEmpty() or self._native_w <= 0 or self._native_h <= 0:
            return QRect()

        x1 = dest.left() + x * dest.width() / self._native_w
        y1 = dest.top() + y * dest.height() / self._native_h
        x2 = dest.left() + (x + w) * dest.width() / self._native_w
        y2 = dest.top() + (y + h) * dest.height() / self._native_h
        return QRect(
            int(round(x1)),
            int(round(y1)),
            max(1, int(round(x2 - x1))),
            max(1, int(round(y2 - y1))),
        )

    def paintEvent(self, event) -> None:  # noqa: ANN001, N802
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(28, 28, 32))

        dest = self._dest_rect()
        if self._pixmap and not dest.isEmpty():
            scaled = self._pixmap.scaled(
                dest.size(),
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            painter.drawPixmap(dest.topLeft(), scaled)

        if self._has_frame and self._native_w > 0 and self._native_h > 0:
            rx, ry, rw, rh = self._region
            wr = self._native_rect_to_widget(rx, ry, rw, rh)
            pen = QPen(QColor(80, 200, 120))
            pen.setWidth(2)
            painter.setPen(pen)
            painter.setBrush(QColor(80, 200, 120, 40))
            painter.drawRect(wr)

        if self._dragging:
            rubber = QRect(self._drag_origin, self._drag_current).normalized()
            pen = QPen(QColor(255, 200, 80))
            pen.setWidth(2)
            pen.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.setBrush(QColor(255, 200, 80, 50))
            painter.drawRect(rubber)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if not self._interactive:
            return super().mousePressEvent(event)
        if event.button() != Qt.MouseButton.LeftButton:
            return
        dest = self._dest_rect()
        if dest.isEmpty() or not self._has_frame:
            return
        pos = event.position().toPoint()
        if not dest.contains(pos):
            return
        self._dragging = True
        self._drag_origin = pos
        self._drag_current = pos
        self.update()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if not self._interactive:
            return super().mouseMoveEvent(event)
        if not self._dragging:
            return
        self._drag_current = event.position().toPoint()
        self.update()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if not self._interactive:
            return super().mouseReleaseEvent(event)
        if not self._dragging or event.button() != Qt.MouseButton.LeftButton:
            return
        self._dragging = False
        self._drag_current = event.position().toPoint()
        rect = QRect(self._drag_origin, self._drag_current).normalized()
        dest = self._dest_rect()
        if not dest.isEmpty():
            rect = rect.intersected(dest)
        if rect.width() >= 3 and rect.height() >= 3:
            x, y, w, h = self._widget_rect_to_native(rect)
            self._region = (x, y, w, h)
            self.region_changed.emit(x, y, w, h)
        self.update()
