#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @FileName  : __init__.py
# @Author    : 雨霓同学
# @Project   : ODPlatform / frame_source
# @Function  : 包入口 — 公共 API re-export
"""
frame_source — 统一帧输入源抽象层

为 YOLO 等目标检测系统提供统一的输入源接口,支持:
    - 摄像头(可配置分辨率/帧率/后端/编码)
    - 视频文件(支持 seek 跳帧)
    - 单张图片
    - 图片文件夹

扩展层(wrappers,正交于具体源):
    - 线程化采集 ThreadedSource — 解决"消费慢拖垮采集"(讲义撞墙⑥)
    - 异步接口   AsyncSource    — 给 async 调用方(web 服务 / MCP server)

────────────────────────────────────────────────────────────────────
设计原则:本模块刻意保持自给自足,可整包拷贝到任何 Python 项目使用。

  外部依赖只有:
    - opencv-python
    - numpy(随 opencv 来)
    - pydantic >= 2.0
    - Python >= 3.10

  ★ 不引用宿主项目的 common / constants / paths 等内部基础设施 ——
    文件扩展名、枚举常量在本模块内部独立定义,与宿主项目同名常量
    内容重叠是巧合,不是约束。
────────────────────────────────────────────────────────────────────

快速使用(三种形态):

    # 1) 同步 — 标准迭代器
    from frame_source import create_frame_source
    with create_frame_source("0") as src:                # 摄像头/视频/图片通吃
        for frame in src:
            process(frame.image)

    # 2) 线程化 — 实时推理首选,解决消费慢拖累采集
    from frame_source import create_threaded_source
    with create_threaded_source("0", warmup_frames=30) as src:
        for frame in src:
            results = model(frame.image)

    # 3) 异步 — 给 async 调用方
    from frame_source import create_async_source
    async with create_async_source("0") as src:
        async for frame in src:
            await async_process(frame.image)

进阶:自定义摄像头参数(高帧率)

    from frame_source import CameraConfig, create_threaded_source
    cfg = CameraConfig(width=1280, height=720, fps=90, backend="msmf")
    with create_threaded_source("0", camera_config=cfg, warmup_frames=30) as src:
        for frame in src:
            print(f"{frame.width}x{frame.height} @ frame {frame.info.frame_index}")
"""
from __future__ import annotations

# ── 类型与抽象 ────────────────────────────────────────────────
from .core.types  import (
    SourceType, FrameInfo, Frame,
    IMAGE_EXTENSIONS, VIDEO_EXTENSIONS,
)
from .core.config import CameraConfig, CameraBackend, CameraCodec
from .core.base   import FrameSource

# ── 具体源实现 ────────────────────────────────────────────────
from .sources.camera import CameraSource
from .sources.video  import VideoSource
from .sources.image  import ImageSource, ImageFolderSource

# ── 包装器(扩展层)────────────────────────────────────────────
from .wrappers.threaded import ThreadedSource, BufferStrategy
from .wrappers.aio      import AsyncSource

# ── 工厂(推荐入口)──────────────────────────────────────────────
from .factory import (
    create_frame_source,
    create_threaded_source,
    create_async_source,
)


__version__ = "2.0.0"
__author__  = "雨霓同学"


__all__ = [
    # 版本元数据
    "__version__",
    "__author__",
    # 类型与抽象
    "SourceType",
    "FrameInfo",
    "Frame",
    "FrameSource",
    "IMAGE_EXTENSIONS",
    "VIDEO_EXTENSIONS",
    # 配置
    "CameraConfig",
    "CameraBackend",
    "CameraCodec",
    # 具体源
    "CameraSource",
    "VideoSource",
    "ImageSource",
    "ImageFolderSource",
    # 包装器
    "ThreadedSource",
    "BufferStrategy",
    "AsyncSource",
    # 工厂(推荐使用)
    "create_frame_source",
    "create_threaded_source",
    "create_async_source",
]