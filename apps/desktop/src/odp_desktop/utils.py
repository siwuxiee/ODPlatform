"""工具函数：帧转换、文件过滤器常量."""

import cv2
import numpy as np
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtCore import QSize, Qt

MAX_DISPLAY_WIDTH = 1920

SUPPORTED_IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp")
SUPPORTED_VIDEO_EXTS = (".mp4", ".avi", ".mov", ".mkv", ".webm")


def bgr_to_qpixmap(bgr: np.ndarray, target_size: QSize | None = None) -> QPixmap:
    """将 BGR numpy 数组（标注帧）转换为 QPixmap 用于显示."""
    h, w = bgr.shape[:2]
    if w > MAX_DISPLAY_WIDTH:
        scale = MAX_DISPLAY_WIDTH / w
        bgr = cv2.resize(bgr, (MAX_DISPLAY_WIDTH, int(h * scale)),
                         interpolation=cv2.INTER_AREA)
        h, w = bgr.shape[:2]

    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    bytes_per_line = 3 * w
    qimg = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
    pixmap = QPixmap.fromImage(qimg)
    if target_size is not None and target_size.isValid():
        pixmap = pixmap.scaled(target_size, Qt.KeepAspectRatio,
                               Qt.SmoothTransformation)
    return pixmap
