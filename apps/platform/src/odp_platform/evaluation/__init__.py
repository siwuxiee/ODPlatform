#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @FileName  : __init__.py
# @Project   : ODPlatform
# @Function  : evaluation 子系统对外公共 API — 只暴露评估专属符号
"""ODPlatform ``evaluation/`` 子系统对外面板.

跟 training/ 同款风格 — 外部调用只 import 顶层包, 不碰内部模块路径.

evaluation/ 只放评估专属(ValService 编排),
跨任务通用工具(model_path / dataset_path / log_rename / config_log / result)全部放
``odp_platform.common.*``. 这一层只暴露真正评估相关的符号:

* ``ValService``   — 评估流程编排
* ``ValResult``    — 评估结果 dataclass
* ``TrainMetrics`` — 指标 dataclass (转再导出, 跟 D6 共用)
* ``val_yolo``     — 便捷函数

下游子系统(D8 InferService)需要 model_path / dataset_path 等
工具时, 应该直接 ``from odp_platform.common.xxx import ...`` — 不要绕道
evaluation. 评估子系统不是这些工具的发行渠道.
"""
from __future__ import annotations

# ---- 核心(2): 评估流程 ----
from .service import ValResult, ValService, val_yolo

# ---- 指标 dataclass: 转再导出 ----
# TrainMetrics 实际定义在 common.result(标注供 D7 共用), 但
# `from odp_platform.evaluation import TrainMetrics` 这个 import 路径足够直观,
# 保留下来让用户的肌肉记忆不破.
from odp_platform.common.result import TrainMetrics

__all__ = [
    "ValService",
    "ValResult",
    "TrainMetrics",
    "val_yolo",
]
