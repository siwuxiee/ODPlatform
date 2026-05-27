#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @FileName  : types.py
# @Author    : 雨霓同学
# @Project   : ODPlatform / frame_source
# @Function  : 核心数据类型 (SourceType / FrameInfo / Frame) + 模块自有扩展名常量
"""
frame_source 核心数据类型定义。

模块独立性原则(规矩 D):
    IMAGE_EXTENSIONS / VIDEO_EXTENSIONS 是 frame_source 的自有 SSoT,
    与宿主项目同名常量内容重叠是巧合,不是约束。本模块不引用任何
    外部基础设施常量,保证整包可拷贝至其他项目。
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

import numpy as np


class SourceType(str, Enum):
    """输入源类型枚举(继承 str 便于序列化与日志)"""
    CAMERA       = "camera"
    VIDEO        = "video"
    IMAGE        = "image"
    IMAGE_FOLDER = "image_folder"


# ── 模块自有 SSoT(frozenset 兼顾不可变 + set 语义)─────────────
# 注: 与宿主项目 common/constants.py 中同名常量内容重叠是巧合,
#     本模块刻意不引用,保证整包可拷贝。
IMAGE_EXTENSIONS: frozenset[str] = frozenset({
    ".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff",
})
VIDEO_EXTENSIONS: frozenset[str] = frozenset({
    ".mp4", ".avi", ".mov", ".mkv", ".flv", ".wmv", ".webm",
})


@dataclass(frozen=True)
class FrameInfo:
    """
    帧元数据(不可变值对象)。

    所有输入源都返回 width/height,供下游计算字体大小/缩放/输出尺寸等。
    """
    # 图像尺寸(所有源都有)
    width: int
    height: int

    # 源信息
    source_type: SourceType
    source_path: str

    # 序列信息
    frame_index: int = 0
    total_frames: Optional[int] = None

    # 时间信息(摄像头 / 视频)
    timestamp: float = 0.0
    fps: Optional[float] = None

    # 文件名(所有源都填充;摄像头填 'camera:<id>' 占位)
    filename: Optional[str] = None

    @property
    def resolution(self) -> tuple[int, int]:
        """分辨率 (width, height)"""
        return (self.width, self.height)


@dataclass
class Frame:
    """
    帧数据(统一返回类型)。

    Attributes:
        image: BGR 格式 ndarray(OpenCV 标准)。默认零拷贝传递,
               调用方需持久保存时自行 .copy()。
        info : 帧元数据
    """
    image: np.ndarray
    info: FrameInfo

    @property
    def resolution(self) -> tuple[int, int]:
        return self.info.resolution

    @property
    def width(self) -> int:
        return self.info.width

    @property
    def height(self) -> int:
        return self.info.height