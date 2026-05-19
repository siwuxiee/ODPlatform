#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @FileName  :init_project.py
# @Time      :2026/5/18 11:34:37
# @Author    :siwuxiee
# @Project   :ODPlatform
# @Function  :

import logging
from pathlib import Path
from typing import List

from odp_platform.common.paths import ROOT_DIR, LOGGING_DIR, get_dirs_to_initialize
from odp_platform.common.logging_utils import get_logger

LINE_WIDTH = 80
logger = logging.getLogger(__name__)

def initialize_project() -> None:
    """
    初始化项目，创建所有必要的目录
    :return: None
    """
    get_logger(
        base_path=LOGGING_DIR,
        log_type="init_project",
        temp_log=False,
    )
    
    logger.info("开始初始化项目核心目录".center(LINE_WIDTH, "="))
    logger.info(f"项目的根目录: {ROOT_DIR}")

    created: List[Path] = []
    existed: List[Path] = []

    for d in get_dirs_to_initialize():
        rel = d.relative_to(ROOT_DIR)
        if d.exists():
            logger.info(f"目录已经存在: {rel}")
            existed.append(d)
        else:
            try:
                d.mkdir(parents=True)
                logger.info(f"成功创建目录: {rel}")
                created.append(d)
            except OSError as e:
                logger.error(f"创建失败: {rel}: {e}")
                raise SystemExit(1) from e

    # 【修复点 2】去掉了 fillchar=
    logger.info("项目核心目录初始化完成".center(LINE_WIDTH, "="))
    logger.info(f"{'目录': <25} | {'状态': <10}")
    logger.info("=" * LINE_WIDTH)
    for d in created:
        logger.info(f"{str(d.relative_to(ROOT_DIR)): <25} | {'新建'}")
    for d in existed:
        logger.info(f"{str(d.relative_to(ROOT_DIR)): <25} | {'已存在'}")
    logger.info("=" * LINE_WIDTH)

if __name__ == "__main__":
    initialize_project()