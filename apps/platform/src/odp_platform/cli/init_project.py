#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @FileName  : init_project.py
# @Author    : 雨霓同学
# @Project   : ODPlatform
# @Function  : 项目运行时目录初始化脚本

import logging
from pathlib import Path
from typing import List

from odp_platform.common.paths import ROOT_DIR, LOGGING_DIR, get_dirs_to_initialize
from odp_platform.common.logging_utils import get_logger

# =====================================================================
# 1. 全局日志系统装配
# 说明: 在 CLI 入口处调用 get_logger()，将 Handler 挂载至根 Logger。
# =====================================================================
get_logger(
    base_path=LOGGING_DIR,
    log_type="init_project",
    temp_log=False
)

# =====================================================================
# 2. 模块级 Logger 实例化
# 说明: 依赖 logging 的冒泡机制，自动继承根 Logger 的 Handler 配置。
# =====================================================================
logger = logging.getLogger(__name__)

def initialize_project() -> None:
    """
    执行项目初始化流程，校验并创建所有必需的运行时目录。
    """
    logger.info(f"启动项目初始化流程，根路径: {ROOT_DIR}")
    
    created: List[Path] = []
    existed: List[Path] = []
    
    for d in get_dirs_to_initialize():
        rel = d.relative_to(ROOT_DIR)
        if d.exists():
            logger.warning(f"目录已存在 (跳过): {rel}")
            existed.append(d)
        else:
            d.mkdir(parents=True, exist_ok=True)
            logger.info(f"目录创建成功: {rel}")
            created.append(d)
            
    logger.info(f"初始化流程结束。共创建 {len(created)} 个目录，已存在 {len(existed)} 个目录。")
    
if __name__ == "__main__":
    initialize_project()