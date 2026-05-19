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

from odp_platform.common.logging_utils import get_logger
from odp_platform.common.string_utils import format_table_row, format_table_separator
# 【修正】修复了老师截图里的 perfirmance 拼写错误
from odp_platform.common.performance_utils import time_it
from odp_platform.common.paths import ROOT_DIR, LOGGING_DIR, RAW_DATA_DIR, get_dirs_to_initialize

LINE_WIDTH = 60
logger = logging.getLogger(__name__)

def _check_raw_data_status() -> List[str]:
    """检查raw数据目录的状态"""
    raw_status: List[str] = []
    rel_raw = RAW_DATA_DIR.relative_to(ROOT_DIR)

    if not RAW_DATA_DIR.exists():
        logger.warning(f"原始数据根目录不存在: {RAW_DATA_DIR}\n"
                       f"请在该目录下创建以【数据集名称】命名的文件夹")
        raw_status.append(f"{rel_raw} 不存在 -> 请创建并放入数据集")
    elif not any(RAW_DATA_DIR.iterdir()):
        logger.warning(f"原始数据根目录为空: {RAW_DATA_DIR}\n"
                       f"预期的数据目录结构: \n"
                       f"  {rel_raw}/ <数据集名称> / \n"
                       f"  ├── images / \n"
                       f"  └── annotations /"
                       )
        raw_status.append(f"{rel_raw} 为空 -> 请放入至少一个数据集")
    else:
        sub_dirs = [p for p in RAW_DATA_DIR.iterdir() if p.is_dir()]
        logger.info(f"原始数据根目录下有 {len(sub_dirs)} 个数据集文件夹")
        raw_status.append(f"{rel_raw} 就绪包含 {len(sub_dirs)} 个数据集")
        for sub in sorted(sub_dirs):
            raw_status.append(f"数据集 {sub.name}")
            
    return raw_status

# 挂载性能测试装饰器
@time_it(iterations=1, name="项目初始化", logger_instance=logger)
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
    
    # 【修正】去掉了 fillchar= 防止报错
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

    # 检查原始数据集目录状态
    # 【修正】去掉了 fillchar=
    logger.info("检查原始数据集目录状态".center(LINE_WIDTH, "="))
    raw_status = _check_raw_data_status()

    # 打印一个汇总信息
    # 【修正】去掉了 fillchar=
    logger.info("项目核心目录初始化完成".center(LINE_WIDTH, "="))
    widths = [30, 12]
    aligns = ['left', 'right']
    logger.info(format_table_row(['目录', '状态'], widths, aligns))
    logger.info(format_table_separator(widths))
    
    for d in created:
        logger.info(format_table_row([str(d.relative_to(ROOT_DIR)), '新建'], widths, aligns))
    for d in existed:
        logger.info(format_table_row([str(d.relative_to(ROOT_DIR)), '已存在'], widths, aligns))
        
    logger.info("=" * LINE_WIDTH)

if __name__ == "__main__":
    initialize_project()