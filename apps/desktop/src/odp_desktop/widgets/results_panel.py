"""结果面板 — 实时统计 + 最终结果 + 日志."""

from PySide6.QtWidgets import (
    QGroupBox, QLabel, QTextEdit, QVBoxLayout,
)
from PySide6.QtCore import Qt


class ResultsPanel(QGroupBox):
    def __init__(self, parent=None) -> None:
        super().__init__("结果", parent)

        self._fps_label = QLabel("FPS: --")
        self._frame_label = QLabel("帧数: --")
        self._det_label = QLabel("检测数: --")
        self._time_label = QLabel("耗时: --")
        self._output_label = QLabel("输出: --")
        self._output_label.setTextInteractionFlags(
            Qt.TextSelectableByMouse
        )

        for lbl in (self._fps_label, self._frame_label, self._det_label,
                     self._time_label, self._output_label):
            lbl.setStyleSheet("padding: 2px 0;")

        self._log_view = QTextEdit()
        self._log_view.setReadOnly(True)
        self._log_view.setMaximumHeight(120)
        self._log_view.setStyleSheet(
            "QTextEdit { background-color: #1e1e1e; color: #aaa; "
            "font-family: monospace; font-size: 11px; }"
        )

        layout = QVBoxLayout(self)
        layout.addWidget(self._fps_label)
        layout.addWidget(self._frame_label)
        layout.addWidget(self._det_label)
        layout.addWidget(self._time_label)
        layout.addWidget(self._output_label)
        layout.addWidget(self._log_view)

    def update_progress(self, data: dict) -> None:
        if "fps_loop" in data:
            self._fps_label.setText(f"FPS: {data['fps_loop']:.1f}")
        if "frame_idx" in data:
            self._frame_label.setText(f"帧数: {data['frame_idx']}")
        if "detections_total" in data:
            self._det_label.setText(f"检测数: {data['detections_total']}")

    def show_result(self, result) -> None:
        if result.success:
            self._time_label.setText(
                f"耗时: {result.infer_time:.1f}s" if result.infer_time
                else "耗时: --"
            )
            self._output_label.setText(
                f"输出: {result.output_dir}"
            )
            self.append_log(f"[完成] 耗时 {result.infer_time:.1f}s, "
                            f"输出目录: {result.output_dir}")
        else:
            self._time_label.setText("耗时: --")
            self.append_log(f"[失败] {result.error}")

    def append_log(self, text: str) -> None:
        self._log_view.append(text)
        # 滚动到底部
        scrollbar = self._log_view.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def clear(self) -> None:
        self._fps_label.setText("FPS: --")
        self._frame_label.setText("帧数: --")
        self._det_label.setText("检测数: --")
        self._time_label.setText("耗时: --")
        self._output_label.setText("输出: --")
        self._log_view.clear()
