#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @FileName  : image.py
# @Author    : 雨霓同学
# @Project   : ODPlatform / frame_source
# @Function  : 单张图片 / 图片文件夹输入源
"""图片输入源(单张 + 文件夹两种形态)。"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional

import cv2
import numpy as np

from ..core.base  import FrameSource
from ..core.types import Frame, FrameInfo, IMAGE_EXTENSIONS, SourceType


logger = logging.getLogger(__name__)


class ImageSource(FrameSource):
    """
    单张图片输入源。

    read() 只返回一次,第二次调用返回 None,符合迭代器"耗尽即停"语义。

    示例:
        with ImageSource("test.jpg") as img:
            frame = img.read()
            print(f"尺寸: {frame.width}x{frame.height}")
    """

    def __init__(self, image_path: str):
        super().__init__(image_path)
        self._image: Optional[np.ndarray] = None
        self._read_count = 0
        self._filename = Path(image_path).name

    def open(self) -> bool:
        self._image = cv2.imread(self.source_path)
        if self._image is None:
            logger.error(f"无法读取图片: {self.source_path}")
            return False
        h, w = self._image.shape[:2]
        logger.info(f"图片已加载: {self._filename} ({w}x{h})")
        return True

    def read(self) -> Optional[Frame]:
        if self._image is None or self._read_count > 0:
            return None

        h, w = self._image.shape[:2]
        info = FrameInfo(
            width=w, height=h,
            source_type=SourceType.IMAGE,
            source_path=self.source_path,
            frame_index=0, total_frames=1,
            filename=self._filename,
        )
        self._read_count += 1
        # 单图源 .copy() 防止外部修改影响后续(虽然 read 只回一次,但保留语义安全)
        return Frame(image=self._image.copy(), info=info)

    def close(self) -> None:
        self._image = None

    def get_source_type(self) -> SourceType:
        return SourceType.IMAGE


class ImageFolderSource(FrameSource):
    """
    图片文件夹输入源。

    注意: 文件夹内每张图片尺寸可能不同,请始终用 frame.width / frame.height
         获取当前帧的实际尺寸,不要假设统一。

    示例:
        with ImageFolderSource("./images") as folder:
            for frame in folder:
                print(f"{frame.info.filename}: {frame.width}x{frame.height}")

        # 跳帧
        with ImageFolderSource("./images") as folder:
            folder.seek(frame=10)
            frame = folder.read()
    """

    def __init__(self, folder_path: str):
        super().__init__(folder_path)
        self._image_files: List[Path] = []
        self._current_index = 0

    def open(self) -> bool:
        folder = Path(self.source_path)
        if not folder.is_dir():
            logger.error(f"不是有效文件夹: {self.source_path}")
            return False

        # ── 撞墙记录: 用 suffix.lower() 过滤而不是 glob("*.jpg")+glob("*.JPG") ──
        # 处理 .Jpg / .jPeG 等混合大小写后缀(Linux 文件系统上真实存在)。
        self._image_files = sorted([
            f for f in folder.iterdir()
            if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
        ])

        if not self._image_files:
            logger.error(f"文件夹中没有支持的图片: {self.source_path}")
            return False

        logger.info(f"文件夹已加载: {folder.name} ({len(self._image_files)} 张)")
        return True

    def read(self) -> Optional[Frame]:
        """读取下一张图片,跳过无法解码的坏图"""
        while self._current_index < len(self._image_files):
            image_path = self._image_files[self._current_index]
            image = cv2.imread(str(image_path))

            if image is None:
                logger.warning(f"无法读取,已跳过: {image_path.name}")
                self._current_index += 1
                continue

            h, w = image.shape[:2]
            info = FrameInfo(
                width=w, height=h,
                source_type=SourceType.IMAGE_FOLDER,
                source_path=self.source_path,
                frame_index=self._current_index,
                total_frames=len(self._image_files),
                filename=image_path.name,
            )
            self._current_index += 1
            return Frame(image=image, info=info)

        return None  # 所有图片遍历完毕

    def seek(
        self,
        frame: Optional[int] = None,
        time_sec: Optional[float] = None,
    ) -> bool:
        """
        跳转到指定图片索引。

        Args:
            frame:    目标图片索引(从 0 开始)
            time_sec: 图片文件夹无时间概念,传入会 warning 并返回 False
        """
        if time_sec is not None:
            logger.warning("图片文件夹不支持按时间跳转,请使用 frame 参数")
            return False
        if frame is None:
            logger.error("必须指定 frame 参数")
            return False

        total = len(self._image_files)
        target = max(0, min(frame, total - 1)) if total > 0 else 0
        self._current_index = target
        logger.debug(f"图片文件夹跳转到索引 {target}")
        return True

    @property
    def seekable(self) -> bool:
        return True

    def close(self) -> None:
        self._image_files = []
        logger.info("文件夹已关闭")

    def get_source_type(self) -> SourceType:
        return SourceType.IMAGE_FOLDER