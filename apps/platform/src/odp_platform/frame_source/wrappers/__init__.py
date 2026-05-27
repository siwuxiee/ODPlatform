#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @FileName  : __init__.py
# @Author    : 雨霓同学
# @Project   : ODPlatform / frame_source
# @Function  : wrappers 子包入口 — 正交扩展层(线程化 / 异步)
"""
wrappers 子包:套在任何 FrameSource 外面的性能/接口扩展层。

不属于任何一种"输入源",而是"输入源的装饰器" —— 跟具体源正交。
"""
from __future__ import annotations

from .threaded import ThreadedSource, BufferStrategy
from .aio      import AsyncSource

__all__ = [
    "ThreadedSource",
    "BufferStrategy",
    "AsyncSource",
]