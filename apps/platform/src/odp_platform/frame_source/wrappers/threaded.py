#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @FileName  : threaded.py
# @Author    : 雨霓同学
# @Project   : ODPlatform / frame_source
# @Function  : ThreadedSource — 把任何 FrameSource 包成后台线程采集
"""
线程化采集包装器。

解决讲义撞墙⑥(显示/推理阻塞采集):
    串行循环里,采集速度 = 最慢环节的速度。imshow + waitKey 会把
    高帧率摄像头(90fps)拖到 60fps 以下,推理更甚。

做法:
    后台 daemon 线程持续 inner.read(),主线程从缓冲拿最新帧 —
    速度解耦,慢消费不再回压采集端。
"""
from __future__ import annotations

import logging
import threading
from queue import Empty, Full, Queue
from typing import Literal, Optional

from ..core.base  import FrameSource
from ..core.types import Frame, SourceType


logger = logging.getLogger(__name__)


BufferStrategy = Literal["latest", "bounded"]


class ThreadedSource(FrameSource):
    """
    把任何 FrameSource 包成"后台线程采集 + 缓冲消费"的形态。

    缓冲策略:
        "latest"  — 队列容量 1,满则丢最旧。实时推理首选,
                    符合"实时系统旧帧无价值,宁丢勿堆"原则。
        "bounded" — 队列容量 buffer_size,满则丢最旧。
                    业务需要尽量不丢中间帧时用(注意:只能降低丢帧率不能根除)。

    所有权:
        被包装的 inner 所有权完全交给 ThreadedSource —— 不要在外部
        read()/seek() 它,否则线程安全无保证。

    示例:
        # 实时推理(默认 latest 缓冲)
        with ThreadedSource(CameraSource(cfg)) as src:
            for frame in src:
                results = model(frame.image)

        # 摄像头预热前 30 帧(MSMF 后端启动期 fps 不稳)
        with ThreadedSource(CameraSource(cfg), warmup_frames=30) as src:
            for frame in src:
                ...

        # bounded 缓冲(允许积压 10 帧)
        with ThreadedSource(VideoSource("x.mp4"), buffer="bounded", buffer_size=10) as src:
            for frame in src:
                ...
    """

    # 哨兵对象:采集线程发现 inner 耗尽时 push 这个,让 read() 知道源结束
    _EOS = object()

    def __init__(
        self,
        inner: FrameSource,
        buffer: BufferStrategy = "latest",
        buffer_size: int = 1,
        warmup_frames: int = 0,
        read_timeout: float = 5.0,
    ):
        # ── 参数验证(fail-fast)──
        if buffer not in ("latest", "bounded"):
            raise ValueError(
                f"buffer 取值必须是 'latest' 或 'bounded',收到: {buffer!r}"
            )
        if buffer_size < 1:
            raise ValueError(f"buffer_size 必须 ≥ 1,收到: {buffer_size}")
        if warmup_frames < 0:
            raise ValueError(f"warmup_frames 必须 ≥ 0,收到: {warmup_frames}")
        if read_timeout <= 0:
            raise ValueError(f"read_timeout 必须 > 0,收到: {read_timeout}")

        super().__init__(inner.source_path)
        self._inner = inner
        self._buffer_strategy = buffer
        # latest 等价于 maxsize=1,统一用 Queue 实现简化代码
        self._capacity = 1 if buffer == "latest" else buffer_size
        self._warmup_frames = warmup_frames
        self._read_timeout = read_timeout

        self._queue: Optional[Queue] = None
        self._capture_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._eos = False    # 调用方视角:源已耗尽

    def open(self) -> bool:
        """打开 inner source 并启动采集线程"""
        if not self._inner.open():
            return False

        self._queue = Queue(maxsize=self._capacity)
        self._stop_event.clear()
        self._eos = False

        self._capture_thread = threading.Thread(
            target=self._capture_loop,
            name=f"ThreadedSource-{self._inner.__class__.__name__}",
            daemon=True,
        )
        self._capture_thread.start()
        logger.info(
            f"采集线程已启动 (buffer={self._buffer_strategy}, "
            f"capacity={self._capacity}, warmup_frames={self._warmup_frames})"
        )
        return True

    # ── 后台采集循环 ────────────────────────────────────────
    def _capture_loop(self) -> None:
        """后台线程主体:不停 read inner,push 到缓冲,直到 stop 或源耗尽"""
        warmup_left = self._warmup_frames
        try:
            while not self._stop_event.is_set():
                frame = self._inner.read()

                if frame is None:
                    # 源耗尽 → push EOS sentinel,让 read() 端能优雅停下
                    self._push(self._EOS)
                    logger.debug("采集线程: inner source 耗尽")
                    return

                # 预热阶段:丢弃前 N 帧(不入队)
                if warmup_left > 0:
                    warmup_left -= 1
                    if warmup_left == 0:
                        logger.debug(f"采集线程: 预热完成({self._warmup_frames} 帧)")
                    continue

                self._push(frame)
        except Exception as e:
            # 采集线程异常不能让调用方永久 hang,push EOS 优雅退出
            logger.error(f"采集线程异常: {e}", exc_info=True)
            self._push(self._EOS)

    def _push(self, item) -> None:
        """
        统一 push:满则丢最旧再放新(实现"宁丢勿堆")。
        latest = maxsize=1 的特例,bounded = maxsize=N。
        """
        try:
            self._queue.put_nowait(item)
        except Full:
            # 满 → 丢最旧 → 重试放新
            try:
                self._queue.get_nowait()
            except Empty:
                pass    # 极罕见的竞态:刚才满,转头空了
            try:
                self._queue.put_nowait(item)
            except Full:
                # 极罕见双重竞态,放弃这一帧(下一帧很快来,实时场景无影响)
                pass

    # ── FrameSource 协议实现 ────────────────────────────────
    def read(self) -> Optional[Frame]:
        """从缓冲拿一帧(阻塞带超时)"""
        if self._eos or self._queue is None:
            return None

        try:
            item = self._queue.get(timeout=self._read_timeout)
        except Empty:
            logger.warning(
                f"采集超时:{self._read_timeout}s 内无新帧抵达缓冲"
            )
            return None

        if item is self._EOS:
            self._eos = True
            return None
        return item

    def close(self) -> None:
        """停止采集线程,关闭 inner source(幂等)"""
        self._stop_event.set()

        if self._capture_thread is not None and self._capture_thread.is_alive():
            self._capture_thread.join(timeout=2.0)
            if self._capture_thread.is_alive():
                logger.warning(
                    "采集线程未在 2 秒内退出(可能 inner.read() 阻塞中)"
                )
        self._capture_thread = None

        self._inner.close()
        logger.info("采集线程已停止,inner source 已关闭")

    def get_source_type(self) -> SourceType:
        """透传 inner 的类型,调用方看不出在用包装器"""
        return self._inner.get_source_type()

    @property
    def seekable(self) -> bool:
        # 线程化采集的"实时流"语义与 seek 冲突,明确不支持。
        # 需要 seek 的场景请直接用 inner source,不要包装。
        return False

    # ── 透传属性(诊断用,不要直接调 inner.read()/seek())──
    @property
    def inner(self) -> FrameSource:
        """访问被包装的 source(调试用)"""
        return self._inner