"""输入源选择面板 — 摄像头 / 图片 / 视频 / 文件夹."""

from PySide6.QtWidgets import (
    QButtonGroup, QCheckBox, QComboBox, QFileDialog, QGroupBox,
    QHBoxLayout, QLineEdit, QPushButton, QRadioButton, QVBoxLayout,
)
from PySide6.QtCore import Signal

from ..utils import SUPPORTED_IMAGE_EXTS, SUPPORTED_VIDEO_EXTS


class SourcePanel(QGroupBox):
    source_changed = Signal(str)
    alert_enabled_changed = Signal(bool)

    def __init__(self, parent=None) -> None:
        super().__init__("输入源", parent)
        self._source_string = "0"
        self._cameras_probed = False

        # -- 模式选择 --
        self._btn_camera = QRadioButton("摄像头")
        self._btn_image = QRadioButton("图片")
        self._btn_video = QRadioButton("视频")
        self._btn_folder = QRadioButton("文件夹")
        self._btn_camera.setChecked(True)

        mode_group = QButtonGroup(self)
        mode_group.addButton(self._btn_camera, 0)
        mode_group.addButton(self._btn_image, 1)
        mode_group.addButton(self._btn_video, 2)
        mode_group.addButton(self._btn_folder, 3)

        mode_row = QHBoxLayout()
        mode_row.addWidget(self._btn_camera)
        mode_row.addWidget(self._btn_image)
        mode_row.addWidget(self._btn_video)
        mode_row.addWidget(self._btn_folder)

        # -- 摄像头选择 --
        self._camera_combo = QComboBox()
        self._camera_combo.addItem("点击扫描摄像头...")

        # -- 路径输入 --
        self._path_edit = QLineEdit()
        self._path_edit.setPlaceholderText("选择文件或文件夹...")
        self._path_edit.setVisible(False)
        self._browse_btn = QPushButton("浏览...")
        self._browse_btn.setVisible(False)

        path_row = QHBoxLayout()
        path_row.addWidget(self._path_edit, 1)
        path_row.addWidget(self._browse_btn)

        # -- 报警选项 (仅摄像头) --
        self._alert_check = QCheckBox("检测到未佩戴安全帽时语音报警")

        # -- 组装 --
        layout = QVBoxLayout(self)
        layout.addLayout(mode_row)
        layout.addWidget(self._camera_combo)
        layout.addLayout(path_row)
        layout.addWidget(self._alert_check)

        # -- 初始状态 (摄像头默认选中) --
        self._alert_check.setVisible(True)

        # -- 信号 --
        mode_group.idClicked.connect(self._on_mode_changed)
        self._camera_combo.activated.connect(self._on_camera_activated)
        self._path_edit.textChanged.connect(self._on_path_changed)
        self._browse_btn.clicked.connect(self._on_browse)
        self._alert_check.toggled.connect(self.alert_enabled_changed.emit)

    def get_source(self) -> str:
        return self._source_string

    def is_alert_enabled(self) -> bool:
        return self._alert_check.isChecked()

    # ------------------------------------------------------------------
    def _probe_cameras(self) -> None:
        if self._cameras_probed:
            return
        import cv2
        self._camera_combo.blockSignals(True)
        self._camera_combo.clear()
        found = False
        for i in range(10):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                cap.release()
                self._camera_combo.addItem(f"摄像头 {i}", str(i))
                found = True
            else:
                cap.release()
        if not found:
            self._camera_combo.addItem("未检测到摄像头", "")
        self._camera_combo.blockSignals(False)
        self._cameras_probed = True

    def _on_camera_activated(self, _index: int) -> None:
        self._probe_cameras()
        data = self._camera_combo.currentData()
        if data:
            self._source_string = data
            self.source_changed.emit(data)

    def _on_mode_changed(self, mode_id: int) -> None:
        if mode_id == 0:  # 摄像头
            self._camera_combo.setVisible(True)
            self._path_edit.setVisible(False)
            self._browse_btn.setVisible(False)
            self._alert_check.setVisible(True)
            self._probe_cameras()
            data = self._camera_combo.currentData()
            self._source_string = data or "0"
        else:
            self._camera_combo.setVisible(False)
            self._path_edit.setVisible(True)
            self._browse_btn.setVisible(True)
            self._alert_check.setVisible(False)

    def _on_path_changed(self, text: str) -> None:
        if text:
            self._source_string = text
            self.source_changed.emit(text)

    def _on_browse(self) -> None:
        if self._btn_image.isChecked():
            filters = (
                f"图片 ({' '.join('*' + e for e in SUPPORTED_IMAGE_EXTS)});;"
                f"所有文件 (*)"
            )
            path, _ = QFileDialog.getOpenFileName(self, "选择图片", "", filters)
        elif self._btn_video.isChecked():
            filters = (
                f"视频 ({' '.join('*' + e for e in SUPPORTED_VIDEO_EXTS)});;"
                f"所有文件 (*)"
            )
            path, _ = QFileDialog.getOpenFileName(self, "选择视频", "", filters)
        else:
            path = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if path:
            self._path_edit.setText(path)
