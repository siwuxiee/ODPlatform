"""画面显示控件 — QLabel 显示标注帧，自适应窗口缩放."""

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget
from PySide6.QtGui import QPixmap, QResizeEvent
from PySide6.QtCore import Qt

from ..utils import bgr_to_qpixmap


class DisplayWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._pixmap: QPixmap | None = None

        self._label = QLabel()
        self._label.setAlignment(Qt.AlignCenter)
        self._label.setMinimumSize(320, 240)
        self._label.setStyleSheet("background-color: #1e1e1e;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._label)

    def set_frame(self, bgr) -> None:
        """槽函数: 接收 BGR numpy 数组并更新显示."""
        self._pixmap = bgr_to_qpixmap(bgr)
        self._label.setPixmap(self._pixmap)

    def clear(self) -> None:
        self._pixmap = None
        self._label.clear()
        self._label.setStyleSheet("background-color: #1e1e1e;")

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if self._pixmap is not None and not self._pixmap.isNull():
            scaled = self._pixmap.scaled(
                self._label.size(), Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            self._label.setPixmap(scaled)
