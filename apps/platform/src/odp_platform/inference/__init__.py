#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @FileName  : __init__.py
# @Project   : ODPlatform
# @Function  : inference 子系统对外公共 API
"""ODPlatform ``inference/`` 子系统对外面板.

D9 改造: 新增 3 个接缝导出, 让 web-backend / desktop 等业务端能直接 import.
原有 4 个符号 (InferService / InferResult / InferStats / infer_yolo) 完全保留, 签名不变.

★ D9 新增导出:
  - OutputSink, LocalFileSink, NullSink  — 输出适配器 (从 .sinks)
  - InferHooks, FrameEvent, ProgressEvent — 生命周期回调 (从 .hooks)
  - CancelToken, InferenceCancelled       — 取消信号 (从 .cancel)

边界承诺 (grep 守门, 跟 D8 一致):
    grep "from odp_platform.training" inference/  → 0 输出
    grep "import fastapi\\|import PyQt\\|import PySide" inference/ → 0 输出
"""
from __future__ import annotations

# ---- D8 原有导出 (签名不变) ----
from .service import InferResult, InferService, InferStats, infer_yolo

# ---- D9 新增导出 ----
from .cancel import CancelToken, InferenceCancelled
from .hooks import FrameEvent, InferHooks, ProgressEvent
from .sinks import LocalFileSink, NullSink, OutputSink

__all__ = [
    # D8 原有
    "InferService",
    "InferResult",
    "InferStats",
    "infer_yolo",
    # D9 新增
    "OutputSink",
    "LocalFileSink",
    "NullSink",
    "InferHooks",
    "FrameEvent",
    "ProgressEvent",
    "CancelToken",
    "InferenceCancelled",
]
