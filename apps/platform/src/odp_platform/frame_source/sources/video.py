#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @FileName  : video.py
# @Author    : 雨霓同学
# @Project   : ODPlatform / frame_source
# @Function  : 视频文件输入源(支持 seek 按帧号/时间跳转)
"""视频文件输入源。"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import cv2

from ..core.base  import FrameSource
from ..core.types import Frame, FrameInfo, SourceType


logger = logging.getLogger(__name__)


class VideoSource(FrameSource):
    """
    视频文件输入源,支持按帧号/时间跳转。

    示例:
        with VideoSource("test.mp4") as video:
            for frame in video:
                print(f"帧 {frame.info.frame_index}/{frame.info.total_frames}")
                print(f"尺寸: {frame.width}x{frame.height}")

        # 跳帧
        with VideoSource("test.mp4") as video:
            video.seek(frame=100)        # 跳到第 100 帧
            video.seek(time_sec=3.5)     # 跳到 3.5 秒
            frame = video.read()
    """

    def __init__(self, video_path: str):
        super().__init__(video_path)
        self._cap: Optional[cv2.VideoCapture] = None
        self._width        = 0
        self._height       = 0
        self._fps          = 0.0
        self._total_frames = 0
        self._filename     = Path(video_path).name

    def open(self) -> bool:
        self._cap = cv2.VideoCapture(self.source_path)
        if not self._cap.isOpened():
            logger.error(f"无法打开视频: {self.source_path}")
            return False

        self._width        = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self._height       = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self._total_frames = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # ── 撞墙记录: FPS 元数据缺失时不静默回退,明确 warning ──
        # 否则 seek(time_sec=...) 会用错误 fps 计算帧号,调用方一无所知。
        raw_fps = self._cap.get(cv2.CAP_PROP_FPS)
        if not raw_fps or raw_fps <= 0:
            logger.warning(
                f"视频 '{self._filename}' FPS 元数据缺失或为 0,"
                f"已回退到默认值 30fps。seek(time_sec=...) 结果可能不准确。"
            )
            self._fps = 30.0
        else:
            self._fps = raw_fps

        logger.info(f"视频已打开: {self._filename}")
        logger.info(f"  分辨率: {self._width}x{self._height} @ {self._fps:.1f}fps")
        logger.info(f"  总帧数: {self._total_frames}")
        return True

    def read(self) -> Optional[Frame]:
        if self._cap is None:
            return None
        ret, image = self._cap.read()
        if not ret:
            return None

        info = FrameInfo(
            width=self._width,
            height=self._height,
            source_type=SourceType.VIDEO,
            source_path=self.source_path,
            frame_index=self._frame_index,
            total_frames=self._total_frames,
            timestamp=self._frame_index / self._fps if self._fps > 0 else 0.0,
            fps=self._fps,
            filename=self._filename,
        )
        self._frame_index += 1
        return Frame(image=image, info=info)

    def seek(
        self,
        frame: Optional[int] = None,
        time_sec: Optional[float] = None,
    ) -> bool:
        """
        跳转到指定位置。

        Args:
            frame:    目标帧号(从 0 开始)
            time_sec: 目标时间(秒)
        """
        if self._cap is None:
            logger.error("视频未打开,无法 seek")
            return False

        # frame 和 time_sec 必须且只能指定一个
        if (frame is None) == (time_sec is None):
            logger.error("frame 和 time_sec 必须且只能指定一个")
            return False

        target = int(time_sec * self._fps) if time_sec is not None else int(frame)
        # 边界夹紧,防越界
        target = max(0, target)
        if self._total_frames > 0:
            target = min(target, self._total_frames - 1)

        ok = self._cap.set(cv2.CAP_PROP_POS_FRAMES, target)
        if ok:
            self._frame_index = target
            logger.debug(f"视频跳转到帧 {target}")
        else:
            logger.warning(f"视频跳转失败:目标帧 {target}")
        return ok

    @property
    def seekable(self) -> bool:
        return True

    @property
    def duration(self) -> float:
        """视频时长(秒);元数据不全时返回 0.0"""
        if self._fps > 0 and self._total_frames > 0:
            return self._total_frames / self._fps
        return 0.0

    def close(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None
            logger.info("视频已关闭")

    def get_source_type(self) -> SourceType:
        return SourceType.VIDEO