#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @FileName  : __init__.py
# @Author    : 雨霓同学
# @Project   : ODPlatform / frame_source
# @Function  : core 子包入口 — 核心类型与抽象
"""core 子包:抽象基类、数据类型、配置定义。"""
from __future__ import annotations

from .types  import SourceType, FrameInfo, Frame, IMAGE_EXTENSIONS, VIDEO_EXTENSIONS
from .config import CameraConfig, CameraBackend, CameraCodec
from .base   import FrameSource

__all__ = [
    "SourceType",
    "FrameInfo",
    "Frame",
    "IMAGE_EXTENSIONS",
    "VIDEO_EXTENSIONS",
    "CameraConfig",
    "CameraBackend",
    "CameraCodec",
    "FrameSource",
]
