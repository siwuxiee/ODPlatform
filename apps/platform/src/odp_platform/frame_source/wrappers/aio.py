#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @FileName  : aio.py
# @Author    : 雨霓同学
# @Project   : ODPlatform / frame_source
# @Function  : AsyncSource — 给 async 调用方的接口包装
"""
异步接口包装器。

⚠️ 实现说明(重要):
    OpenCV 的 read() 是阻塞 C 调用,在 asyncio event loop 里直接调用
    会噎死整个 loop。本类通过 asyncio.to_thread() 把阻塞调用扔到默认
    线程池,保证 event loop 流畅 — 但这意味着 AsyncSource 本身只
    提供 "async 友好的协议",不提供"采集与消费并行"。

    需要真正的"采集/推理并行"时,把 ThreadedSource 嵌在内部:

        async with AsyncSource(ThreadedSource(CameraSource(cfg))) as src:
            async for frame in src:
                await async_process(frame.image)

    外层提供 async 协议给调用方,内层 ThreadedSource 让采集后台跑 —
    两层职责正交,组合即可。
"""
from __future__ import annotations

import asyncio
import logging
from typing import AsyncIterator, Optional

from ..core.base  import FrameSource
from ..core.types import Frame


logger = logging.getLogger(__name__)


class AsyncSource:
    """
    把任何 FrameSource 包成 async 接口。

    注意:本类不继承 FrameSource —— async 协议与同步协议的方法签名
    不兼容(同步 def vs async def),强行继承会破坏 LSP。它通过
    `inner` 属性持有内部源,在协议层面与 FrameSource"等位",不"is-a"。

    示例:
        # 基础:async 接口,内部仍然单线程阻塞采集(适合视频/图片)
        async with AsyncSource(create_frame_source("video.mp4")) as src:
            async for frame in src:
                await async_process(frame.image)

        # 推荐:async 接口 + 后台线程采集(摄像头实时推理)
        async with AsyncSource(ThreadedSource(CameraSource(cfg))) as src:
            async for frame in src:
                await async_process(frame.image)
    """

    def __init__(self, inner: FrameSource):
        self._inner = inner

    # ── async 版 FrameSource 协议 ───────────────────────────
    async def open(self) -> bool:
        return await asyncio.to_thread(self._inner.open)

    async def read(self) -> Optional[Frame]:
        return await asyncio.to_thread(self._inner.read)

    async def close(self) -> None:
        await asyncio.to_thread(self._inner.close)

    async def seek(
        self,
        frame: Optional[int] = None,
        time_sec: Optional[float] = None,
    ) -> bool:
        return await asyncio.to_thread(self._inner.seek, frame, time_sec)

    @property
    def seekable(self) -> bool:
        return self._inner.seekable

    @property
    def source_path(self) -> str:
        return self._inner.source_path

    @property
    def inner(self) -> FrameSource:
        """访问被包装的源(诊断用)"""
        return self._inner

    # ── async 上下文管理器协议 ───────────────────────────────
    async def __aenter__(self) -> "AsyncSource":
        await self.open()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        await self.close()
        return False  # 不吞异常

    # ── async 迭代器协议 ─────────────────────────────────────
    def __aiter__(self) -> AsyncIterator[Frame]:
        return self

    async def __anext__(self) -> Frame:
        frame = await self.read()
        if frame is None:
            raise StopAsyncIteration
        return frame