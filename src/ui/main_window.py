from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import cv2
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from src.services.task_service import TaskService
from src.ui.widgets.region_selector import RegionSelector
from src.ui.widgets.video_preview import VideoPreview
from src.utils.paths import cache_root, output_root
from src.video.ffmpeg_paths import FFmpegNotFoundError, resolve_ffmpeg, resolve_ffprobe
from src.video.ffmpeg_probe import FFmpegProbeError, probe_video


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("VidEraser")
        self.resize(980, 640)
        self.selected_video: Path | None = None
        self.task_service = TaskService(cache_root=cache_root(), output_root=output_root())
        self.current_worker = None
        self.current_output_path: str | None = None
        self.ffmpeg_ready = False
        self.video_width = 0
        self.video_height = 0
        self._build_ui()
        self.run_startup_checks()

    def _build_ui(self) -> None:
        wrapper = QWidget(self)
        self.setCentralWidget(wrapper)
        layout = QVBoxLayout(wrapper)

        self.video_path_label = QLabel("未选择视频")
        self.video_path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.video_path_label)
        self.video_meta_label = QLabel("视频信息: -")
        layout.addWidget(self.video_meta_label)

        self.video_preview = VideoPreview(self)
        self.video_preview.setMinimumHeight(220)
        layout.addWidget(self.video_preview)

        button_row = QHBoxLayout()
        self.btn_import = QPushButton("导入视频")
        self.btn_start = QPushButton("开始任务")
        self.btn_cancel = QPushButton("取消任务")
        self.btn_open_output = QPushButton("打开输出目录")
        self.btn_start.setEnabled(False)
        self.btn_cancel.setEnabled(False)
        self.btn_open_output.setEnabled(True)

        button_row.addWidget(self.btn_import)
        button_row.addWidget(self.btn_start)
        button_row.addWidget(self.btn_cancel)
        button_row.addWidget(self.btn_open_output)
        layout.addLayout(button_row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        layout.addWidget(self.progress)

        self.region_selector = RegionSelector(self)
        layout.addWidget(self.region_selector)

        self.log_box = QPlainTextEdit()
        self.log_box.setReadOnly(True)
        layout.addWidget(self.log_box, stretch=1)

        self.btn_import.clicked.connect(self.on_import_video)
        self.btn_start.clicked.connect(self.on_start_task)
        self.btn_cancel.clicked.connect(self.on_cancel_task)
        self.btn_open_output.clicked.connect(self.on_open_output_dir)

        self.region_selector.region_changed.connect(self._on_region_spin_changed)
        self.video_preview.region_changed.connect(self._on_preview_region_changed)

    def _append_log(self, text: str) -> None:
        self.log_box.appendPlainText(text)

    def run_startup_checks(self) -> None:
        try:
            ffprobe_bin = resolve_ffprobe()
            ffmpeg_bin = resolve_ffmpeg()
            self.ffmpeg_ready = True
            self._append_log(f"FFprobe: {ffprobe_bin}")
            self._append_log(f"FFmpeg: {ffmpeg_bin}")
        except FFmpegNotFoundError as exc:
            self.ffmpeg_ready = False
            self.video_meta_label.setText("视频信息: 未检测到 FFmpeg（请先安装）")
            self._append_log(str(exc))
            QMessageBox.warning(self, "启动自检", str(exc))

    def on_import_video(self) -> None:
        if not self.ffmpeg_ready:
            QMessageBox.warning(self, "缺少 FFmpeg", "请先安装 FFmpeg 后再导入视频。")
            return
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择视频文件",
            "",
            "Videos (*.mp4 *.mov *.mkv *.avi *.flv *.webm)",
        )
        if not file_path:
            return
        self.selected_video = Path(file_path)
        self.video_path_label.setText(str(self.selected_video))
        self.btn_start.setEnabled(True)
        self._append_log(f"已导入视频: {self.selected_video}")
        try:
            info = probe_video(self.selected_video)
            video_stream = next(
                (s for s in info.get("streams", []) if s.get("codec_type") == "video"),
                {},
            )
            width = video_stream.get("width", "?")
            height = video_stream.get("height", "?")
            fps = video_stream.get("avg_frame_rate", "?")
            duration = info.get("format", {}).get("duration", "?")
            meta = f"视频信息: {width}x{height}, fps={fps}, duration={duration}s"
            self.video_meta_label.setText(meta)
            self._append_log(meta)
            self.video_width = int(width) if str(width).isdigit() else 0
            self.video_height = int(height) if str(height).isdigit() else 0
            self._load_preview_frame()
            if self.video_width <= 0 or self.video_height <= 0:
                nw, nh = self.video_preview.native_size()
                if nw > 0 and nh > 0:
                    self.video_width = nw
                    self.video_height = nh
            if self.video_width > 0 and self.video_height > 0:
                self.region_selector.set_frame_size(self.video_width, self.video_height)
                region = self.region_selector.get_region()
                self.video_preview.set_region_native(*region)
                self._append_log(f"当前区域: {region}（可在预览上拖拽框选）")
        except FFmpegNotFoundError as exc:
            self.video_meta_label.setText("视频信息: 未安装 FFmpeg（缺少 ffprobe）")
            self._append_log(str(exc))
            QMessageBox.warning(self, "缺少 FFmpeg", str(exc))
        except FFmpegProbeError as exc:
            self.video_meta_label.setText("视频信息: ffprobe 读取失败")
            self._append_log(f"读取视频信息失败: {exc}")

    def _load_preview_frame(self) -> None:
        self.video_preview.clear()
        if not self.selected_video:
            return
        cap = cv2.VideoCapture(str(self.selected_video))
        try:
            ok, frame = cap.read()
        finally:
            cap.release()
        if not ok or frame is None:
            self._append_log("预览: 无法读取首帧，请检查视频是否可读")
            return
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        fh, fw = rgb.shape[:2]
        qimg = QImage(
            rgb.data,
            fw,
            fh,
            rgb.strides[0],
            QImage.Format.Format_RGB888,
        ).copy()
        nw = self.video_width if self.video_width > 0 else fw
        nh = self.video_height if self.video_height > 0 else fh
        self.video_preview.set_preview_image(qimg, nw, nh)

    def _on_region_spin_changed(self, region: tuple[int, int, int, int]) -> None:
        x, y, w, h = region
        self.video_preview.set_region_native(x, y, w, h)

    def _on_preview_region_changed(self, x: int, y: int, w: int, h: int) -> None:
        self.region_selector.set_region_silent(x, y, w, h)
        self._append_log(f"预览框选区域: ({x}, {y}, {w}, {h})")

    def on_start_task(self) -> None:
        if not self.ffmpeg_ready:
            QMessageBox.warning(self, "缺少 FFmpeg", "请先安装 FFmpeg 后再开始任务。")
            return
        if not self.selected_video:
            QMessageBox.warning(self, "提示", "请先导入视频。")
            return

        task = self.task_service.create_task(self.selected_video)
        task.selected_region = self.video_preview.get_region_native()
        self.region_selector.set_region_silent(*task.selected_region)
        self._append_log(f"[{task.task_id}] 使用区域: {task.selected_region}")
        worker = self.task_service.start_task(task)
        self.current_worker = worker
        worker.signals.progress.connect(self.on_progress)
        worker.signals.log.connect(self.on_log)
        worker.signals.error.connect(self.on_error)
        worker.signals.done.connect(self.on_done)
        worker.signals.cancelled.connect(self.on_cancelled)
        worker.signals.preview.connect(self.on_preview)

        self.progress.setValue(0)
        self.btn_start.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self._append_log(f"[{task.task_id}] 任务启动")

    def on_cancel_task(self) -> None:
        self.task_service.cancel_current_task()
        self.btn_cancel.setEnabled(False)

    def on_open_output_dir(self) -> None:
        out = str(output_root())
        if sys.platform == "darwin":
            subprocess.run(["open", out], check=False)
        elif os.name == "nt":
            os.startfile(out)  # type: ignore[attr-defined]
        else:
            subprocess.run(["xdg-open", out], check=False)

    def on_progress(self, task_id: str, stage: str, percent: float, eta: int) -> None:
        self.progress.setValue(int(percent))
        self._append_log(f"[{task_id}] {stage}: {percent:.1f}% ETA {eta}s")

    def on_log(self, task_id: str, level: str, message: str) -> None:
        self._append_log(f"[{task_id}] {level.upper()}: {message}")

    def on_error(self, task_id: str, code: str, message: str, detail: str) -> None:
        self.btn_start.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self._append_log(f"[{task_id}] ERROR {code}: {message}")
        QMessageBox.critical(self, "任务失败", f"{message}\n\n{detail}")

    def on_done(self, task_id: str, output_path: str, metrics: dict) -> None:
        self.current_output_path = output_path
        self.btn_start.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self._append_log(f"[{task_id}] DONE: {output_path}")
        self._append_log(f"[{task_id}] metrics: {metrics}")
        QMessageBox.information(self, "任务完成", f"输出文件：\n{output_path}")

    def on_cancelled(self, task_id: str) -> None:
        self.btn_start.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self._append_log(f"[{task_id}] 已取消")

    def on_preview(self, task_id: str, frame_path: str) -> None:
        self._append_log(f"[{task_id}] preview frame: {frame_path}")


def apply_dark_theme(app: QApplication) -> None:
    qss_path = Path(__file__).resolve().parent / "themes" / "dark.qss"
    if qss_path.exists():
        app.setStyleSheet(qss_path.read_text(encoding="utf-8"))


def run_app() -> None:
    app = QApplication(sys.argv)
    apply_dark_theme(app)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
