"""模型设置面板 — 模型文件选择 + 置信度 / IoU 阈值."""

from pathlib import Path

from PySide6.QtWidgets import (
    QDoubleSpinBox, QFileDialog, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QSlider, QVBoxLayout,
)
from PySide6.QtCore import Qt, Signal


class ModelPanel(QGroupBox):
    model_changed = Signal(str)
    conf_changed = Signal(float)
    iou_changed = Signal(float)

    def __init__(self, parent=None) -> None:
        super().__init__("模型设置", parent)

        # -- 模型文件 --
        model_label = QLabel("模型文件:")
        self._model_edit = QLineEdit()
        self._model_edit.setPlaceholderText("选择 .pt 模型文件...")
        browse_btn = QPushButton("浏览...")
        model_row = QHBoxLayout()
        model_row.addWidget(model_label)
        model_row.addWidget(self._model_edit, 1)
        model_row.addWidget(browse_btn)

        # -- 置信度 --
        conf_label = QLabel("置信度:")
        self._conf_slider = QSlider(Qt.Horizontal)
        self._conf_slider.setRange(0, 100)
        self._conf_slider.setValue(25)
        self._conf_spin = QDoubleSpinBox()
        self._conf_spin.setRange(0.0, 1.0)
        self._conf_spin.setSingleStep(0.05)
        self._conf_spin.setValue(0.25)
        conf_row = QHBoxLayout()
        conf_row.addWidget(conf_label)
        conf_row.addWidget(self._conf_slider, 1)
        conf_row.addWidget(self._conf_spin)

        # -- IoU --
        iou_label = QLabel("IoU:")
        self._iou_slider = QSlider(Qt.Horizontal)
        self._iou_slider.setRange(0, 100)
        self._iou_slider.setValue(70)
        self._iou_spin = QDoubleSpinBox()
        self._iou_spin.setRange(0.0, 1.0)
        self._iou_spin.setSingleStep(0.05)
        self._iou_spin.setValue(0.70)
        iou_row = QHBoxLayout()
        iou_row.addWidget(iou_label)
        iou_row.addWidget(self._iou_slider, 1)
        iou_row.addWidget(self._iou_spin)

        # -- 输出目录 --
        out_label = QLabel("输出目录:")
        self._output_edit = QLineEdit()
        self._output_edit.setPlaceholderText("留空 = 默认 (runs/detect_infer/predict/)")
        out_browse_btn = QPushButton("浏览...")
        out_row = QHBoxLayout()
        out_row.addWidget(out_label)
        out_row.addWidget(self._output_edit, 1)
        out_row.addWidget(out_browse_btn)

        layout = QVBoxLayout(self)
        layout.addLayout(model_row)
        layout.addLayout(conf_row)
        layout.addLayout(iou_row)
        layout.addLayout(out_row)

        # -- 信号 --
        browse_btn.clicked.connect(self._on_browse)
        self._model_edit.textChanged.connect(
            lambda t: self.model_changed.emit(t)
        )
        self._conf_slider.valueChanged.connect(self._on_conf_slider)
        self._conf_spin.valueChanged.connect(self._on_conf_spin)
        self._iou_slider.valueChanged.connect(self._on_iou_slider)
        self._iou_spin.valueChanged.connect(self._on_iou_spin)
        out_browse_btn.clicked.connect(self._on_out_browse)

    def set_model_path(self, path: str) -> None:
        self._model_edit.setText(path)

    def get_model_path(self) -> str:
        return self._model_edit.text()

    def get_conf(self) -> float:
        return self._conf_spin.value()

    def get_iou(self) -> float:
        return self._iou_spin.value()

    def get_output_dir(self) -> str:
        return self._output_edit.text()

    # ------------------------------------------------------------------
    def _on_browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "选择模型文件", "",
            "PyTorch 模型 (*.pt);;所有文件 (*)",
        )
        if path:
            self._model_edit.setText(path)

    def _on_conf_slider(self, value: int) -> None:
        self._conf_spin.blockSignals(True)
        self._conf_spin.setValue(value / 100.0)
        self._conf_spin.blockSignals(False)
        self.conf_changed.emit(value / 100.0)

    def _on_conf_spin(self, value: float) -> None:
        self._conf_slider.blockSignals(True)
        self._conf_slider.setValue(int(value * 100))
        self._conf_slider.blockSignals(False)
        self.conf_changed.emit(value)

    def _on_iou_slider(self, value: int) -> None:
        self._iou_spin.blockSignals(True)
        self._iou_spin.setValue(value / 100.0)
        self._iou_spin.blockSignals(False)
        self.iou_changed.emit(value / 100.0)

    def _on_iou_spin(self, value: float) -> None:
        self._iou_slider.blockSignals(True)
        self._iou_slider.setValue(int(value * 100))
        self._iou_slider.blockSignals(False)
        self.iou_changed.emit(value)

    def _on_out_browse(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if path:
            self._output_edit.setText(path)
