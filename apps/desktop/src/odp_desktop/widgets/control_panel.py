"""控制面板 — 开始 / 停止 / 暂停按钮 + 进度条."""

from PySide6.QtWidgets import (
    QGroupBox, QHBoxLayout, QProgressBar, QPushButton, QVBoxLayout,
)
from PySide6.QtCore import Signal


class ControlPanel(QGroupBox):
    start_requested = Signal()
    stop_requested = Signal()
    pause_toggled = Signal(bool)

    def __init__(self, parent=None) -> None:
        super().__init__("控制", parent)

        self._start_btn = QPushButton("开始")
        self._stop_btn = QPushButton("停止")
        self._pause_btn = QPushButton("暂停")
        self._pause_btn.setCheckable(True)

        self._stop_btn.setEnabled(False)
        self._pause_btn.setEnabled(False)

        self._start_btn.setStyleSheet(
            "QPushButton { background-color: #2e7d32; color: white; "
            "font-weight: bold; padding: 6px 16px; }"
            "QPushButton:hover { background-color: #388e3c; }"
        )
        self._stop_btn.setStyleSheet(
            "QPushButton { background-color: #c62828; color: white; "
            "font-weight: bold; padding: 6px 16px; }"
            "QPushButton:hover { background-color: #d32f2f; }"
        )

        btn_row = QHBoxLayout()
        btn_row.addWidget(self._start_btn)
        btn_row.addWidget(self._pause_btn)
        btn_row.addWidget(self._stop_btn)

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.setVisible(False)

        layout = QVBoxLayout(self)
        layout.addLayout(btn_row)
        layout.addWidget(self._progress)

        # -- 信号 --
        self._start_btn.clicked.connect(self._on_start)
        self._stop_btn.clicked.connect(self._on_stop)
        self._pause_btn.toggled.connect(self._on_pause)

    def set_running(self, running: bool) -> None:
        self._start_btn.setEnabled(not running)
        self._stop_btn.setEnabled(running)
        self._pause_btn.setEnabled(running)
        if not running:
            self._pause_btn.setChecked(False)
            self._progress.setVisible(False)

    def set_progress(self, value: int, maximum: int = 0) -> None:
        if maximum > 0:
            self._progress.setRange(0, maximum)
            self._progress.setValue(value)
        else:
            self._progress.setRange(0, 0)
        self._progress.setVisible(True)

    # ------------------------------------------------------------------
    def _on_start(self) -> None:
        self.start_requested.emit()

    def _on_stop(self) -> None:
        self.stop_requested.emit()

    def _on_pause(self, checked: bool) -> None:
        self.pause_toggled.emit(checked)
