#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @FileName  : base.py
# @Author    : 雨霓同学
# @Project   : ODPlatform / frame_source
# @Function  : FrameSource 抽象基类 — 统一所有输入源的协议
"""
帧源抽象基类。定义所有输入源(摄像头/视频/图片/包装器)共享的协议:

    open / read / close + seek (可选) + 上下文管理器 + 迭代器
"""
from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from typing import Iterator, Optional

from .types import Frame, SourceType


logger = logging.getLogger(__name__)


class FrameSource(ABC):
    """
    帧源抽象基类。

    标准用法:
        with SomeSource(...) as source:
            for frame in source:
                process(frame.image)
                print(frame.width, frame.height)

    跳帧(仅 seekable=True 的源支持):
        source.seek(frame=100)      # 跳到第 100 帧
        source.seek(time_sec=3.5)   # 跳到 3.5 秒

    注意:
        同一 source 对象只能迭代一次(标准迭代器协议)。
        需要重头迭代请重新 open() 或重新创建对象。
    """

    def __init__(self, source_path: str):
        self.source_path = source_path
        self._frame_index = 0
        self._start_time = time.time()

    # ── 子类必须实现 ────────────────────────────────────────
    @abstractmethod
    def open(self) -> bool:
        """打开输入源,返回是否成功"""

    @abstractmethod
    def read(self) -> Optional[Frame]:
        """读取一帧,源耗尽时返回 None"""

    @abstractmethod
    def close(self) -> None:
        """关闭输入源,释放资源"""

    @abstractmethod
    def get_source_type(self) -> SourceType:
        """返回输入源类型"""

    # ── seek 协议(默认不支持,子类按需覆盖)─────────────────
    def seek(
        self,
        frame: Optional[int] = None,
        time_sec: Optional[float] = None,   # 参数名 time_sec 避免与 time 模块冲突
    ) -> bool:
        """
        跳转到指定位置(基类默认不支持)。

        Args:
            frame:    目标帧号(从 0 开始)
            time_sec: 目标时间(秒)

        Returns:
            是否成功
        """
        logger.warning(f"{self.__class__.__name__} 不支持 seek 操作")
        return False

    @property
    def seekable(self) -> bool:
        """是否支持 seek,子类覆盖返回 True"""
        return False

    # ── 上下文管理器协议 ────────────────────────────────────
    def __enter__(self) -> "FrameSource":
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        self.close()
        return False  # 不吞异常

    # ── 迭代器协议 ──────────────────────────────────────────
    def __iter__(self) -> Iterator[Frame]:
        return self

    def __next__(self) -> Frame:
        frame = self.read()
        if frame is None:
            raise StopIteration
        return frame