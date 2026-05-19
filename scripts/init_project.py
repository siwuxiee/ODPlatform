#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @FileName  :init_project.py
# @Time      :2026/5/19 10:28:46
# @Author    :雨霓同学
# @Project   :ODPlatform
# @Function  :
"""
ODPlatform项目初始化入口(开发阶段)
"""

import sys
from pathlib import Path

# 向上找两层，定位到 ODPlatform 根目录
REPO_ROOT = Path(__file__).resolve().parent.parent
# 拼接出 src 目录的绝对路径
PLATFORM_SRC = REPO_ROOT / "apps" / "platform" / "src"

# 动态将 src 目录插入到 Python 的环境变量最前面
sys.path.insert(0, str(PLATFORM_SRC))

# 现在可以安全地导入你之前写的核心逻辑了
from odp_platform.cli.init_project import initialize_project

if __name__ == "__main__":
    initialize_project()