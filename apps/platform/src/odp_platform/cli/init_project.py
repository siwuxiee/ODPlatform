#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @FileName  :init_project.py
# @Time      :2026/5/18 11:34:37
# @Author    :雨霓同学
# @Project   :ODPlatform
# @Function  :

import logging
from pathlib import Path
from typing import List

from odp_platform.common.paths import ROOT_DIR, LOGGING_DIR, get_dirs_to_initialize
from odp_platform.common.logging_utils import get_logger
# 【新增导入】引入你刚写的字符串排版工具
from odp_platform.common.string_utils import format_table_row, format_table_separator

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

    # =================================================================
    # 【核心改造区】使用 string_utils 打印完美对齐的表格
    # =================================================================
    logger.info("项目核心目录初始化完成".center(LINE_WIDTH, "="))
    
    # 1. 定义表格的列宽和对齐方式
    col_widths = [40, 10]
    col_aligns = ['left', 'right']
    
    # 2. 打印表头
    header = format_table_row(['目录 (Directory)', '状态 (Status)'], col_widths, col_aligns)
    logger.info(header)
    
    # 3. 打印分隔线 (使用工具类生成匹配宽度的线)
    separator = format_table_separator(col_widths, char="-")
    logger.info(separator)
    
    # 4. 打印数据行
    for d in created:
        row_str = format_table_row([str(d.relative_to(ROOT_DIR)), '新建'], col_widths, col_aligns)
        logger.info(row_str)
        
    for d in existed:
        row_str = format_table_row([str(d.relative_to(ROOT_DIR)), '已存在'], col_widths, col_aligns)
        logger.info(row_str)
        
    logger.info("=" * LINE_WIDTH)

if __name__ == "__main__":
    initialize_project()