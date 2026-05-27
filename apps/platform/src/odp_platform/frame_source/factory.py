#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @FileName  : factory.py
# @Author    : 雨霓同学
# @Project   : ODPlatform / frame_source
# @Function  : 工厂函数 — 字符串自动识别 + 包装器组合便捷入口
"""
工厂函数(三件套)。

设计:
    create_frame_source     — 字符串自动识别 → 同步源(基础,单一职责)
    create_threaded_source  — 上面再包 ThreadedSource(实时推理首选)
    create_async_source     — 上面再包 AsyncSource (async 调用方用)
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from .core.base   import FrameSource
from .core.config import CameraConfig
from .core.types  import IMAGE_EXTENSIONS, VIDEO_EXTENSIONS
from .sources.camera import CameraSource
from .sources.video  import VideoSource
from .sources.image  import ImageFolderSource, ImageSource
from .wrappers.threaded import BufferStrategy, ThreadedSource
from .wrappers.aio      import AsyncSource


def create_frame_source(
    source: str,
    camera_config: Optional[CameraConfig] = None,
) -> FrameSource:
    """
    自动识别输入源类型,返回对应的 FrameSource 子类实例(未 open)。

    Args:
        source: 输入源标识
            - "0", "1", "2" ... → 摄像头(设备 ID)
            - "video.mp4"       → 视频文件
            - "image.jpg"       → 单张图片
            - "./images/"       → 图片文件夹
        camera_config: 摄像头配置,仅 source 为摄像头 ID 时生效
            - None       使用默认 CameraConfig
            - 提供时     自动用 source 中的 ID 覆盖 camera_id 字段
                         (model_copy 不污染调用方原对象)

    Returns:
        FrameSource 子类实例(未 open,请配合 with 或手动 open() 使用)

    Raises:
        ValueError: 路径不存在 / 格式不支持 / 无法识别输入源类型

    Examples:
        # 摄像头(默认配置)
        source = create_frame_source("0")

        # 摄像头(自定义高帧率配置)
        config = CameraConfig(width=1280, height=720, fps=90, backend="msmf")
        source = create_frame_source("0", camera_config=config)

        # 视频文件
        source = create_frame_source("test.mp4")

        # 单张图片
        source = create_frame_source("test.jpg")

        # 图片文件夹
        source = create_frame_source("./images")
    """
    # ── 摄像头:纯数字字符串 ────────────────────────────────
    if source.isdigit():
        camera_id = int(source)
        if camera_config is None:
            config = CameraConfig(camera_id=camera_id)
        else:
            # Pydantic v2 副本,不污染调用方传入的原对象
            config = camera_config.model_copy(update={"camera_id": camera_id})
        return CameraSource(config)

    # ── 文件 / 文件夹路径 ──────────────────────────────────
    path = Path(source)
    # 先检查存在性,路径不存在立刻报错(fail-fast)
    if not path.exists():
        raise ValueError(f"路径不存在: {source}")

    if path.is_dir():
        return ImageFolderSource(source)

    ext = path.suffix.lower()
    if ext in VIDEO_EXTENSIONS:
        return VideoSource(source)
    if ext in IMAGE_EXTENSIONS:
        return ImageSource(source)

    raise ValueError(
        f"不支持的文件格式: '{ext}'\n"
        f"  支持的视频格式: {sorted(VIDEO_EXTENSIONS)}\n"
        f"  支持的图片格式: {sorted(IMAGE_EXTENSIONS)}"
    )


def create_threaded_source(
    source: str,
    camera_config: Optional[CameraConfig] = None,
    *,
    buffer: BufferStrategy = "latest",
    buffer_size: int = 1,
    warmup_frames: int = 0,
    read_timeout: float = 5.0,
) -> ThreadedSource:
    """
    便捷工厂:自动识别 + 线程化包装。**实时推理场景首选**。

    解决讲义撞墙⑥(消费慢拖累采集)— 采集放后台线程,消费端从缓冲拿最新帧。

    Args:
        source / camera_config: 同 create_frame_source
        buffer:        "latest"(默认) 只留最新帧 / "bounded" 有界队列
        buffer_size:   bounded 模式下的队列容量
        warmup_frames: 启动后丢弃前 N 帧(摄像头 MSMF 后端前 30 帧 fps 不稳)
        read_timeout:  read() 等待新帧的超时(秒)

    Examples:
        # 摄像头实时推理(典型用法)
        with create_threaded_source("0", warmup_frames=30) as src:
            for frame in src:
                results = model(frame.image)

        # 自定义摄像头参数
        cfg = CameraConfig(width=1280, height=720, fps=90, backend="msmf")
        with create_threaded_source("0", camera_config=cfg, warmup_frames=30) as src:
            for frame in src:
                ...
    """
    inner = create_frame_source(source, camera_config=camera_config)
    return ThreadedSource(
        inner,
        buffer=buffer,
        buffer_size=buffer_size,
        warmup_frames=warmup_frames,
        read_timeout=read_timeout,
    )


def create_async_source(
    source: str,
    camera_config: Optional[CameraConfig] = None,
    *,
    threaded: bool = True,
    buffer: BufferStrategy = "latest",
    buffer_size: int = 1,
    warmup_frames: int = 0,
    read_timeout: float = 5.0,
) -> AsyncSource:
    """
    便捷工厂:自动识别 +(可选线程化)+ async 接口包装。

    给 async 调用方使用(web 服务 / MCP server / 异步推理 pipeline 等)。

    Args:
        source / camera_config: 同 create_frame_source
        threaded: 默认 True —— 内部嵌一层 ThreadedSource,让采集在后台线程跑,
                  实现"async 接口 + 真正并行采集"。
                  设为 False 时只是把同步源包成 async 协议,不提供并行
                  (适合视频/图片等本身不存在"采集速率"概念的场景)。
        buffer / buffer_size / warmup_frames / read_timeout:
                  仅 threaded=True 时生效,语义同 create_threaded_source

    Examples:
        # 摄像头 async + 线程化(默认,真正并行)
        async with create_async_source("0", warmup_frames=30) as src:
            async for frame in src:
                await async_process(frame.image)

        # 视频文件 async(不需要线程化)
        async with create_async_source("video.mp4", threaded=False) as src:
            async for frame in src:
                ...
    """
    inner: FrameSource = create_frame_source(source, camera_config=camera_config)
    if threaded:
        inner = ThreadedSource(
            inner,
            buffer=buffer,
            buffer_size=buffer_size,
            warmup_frames=warmup_frames,
            read_timeout=read_timeout,
        )
    return AsyncSource(inner)