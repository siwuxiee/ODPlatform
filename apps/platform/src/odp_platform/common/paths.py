#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @FileName  :paths.py
# @Time      :2026/5/18 11:53:15
# @Author    :siwuxiee
# @Project   :ODPlatform
# @Function  :
from pathlib import Path
from typing import List, Tuple

WORKSPACE_MARKER: str = ".odp-workspace"

def _find_workspace_root(
        start: Path,
        markers: Tuple[str, ...] = (WORKSPACE_MARKER, ),
) -> Path:
    """
    从start开始沿着父目录向上查找，返回包含任一marker文件的目录
    :param start: 起始路径
    :param markers: 一组marker文件名，只要存在一个就视为找到
    :return: workspace根目录
    :raise: 一直爬到文件系统系统都没找到，返回一个FileNotFoundError
    """
    current = start.resolve()
    if current.is_file():
        current = current.parent

    for parent in [current.parent, *current.parents]:
        for marker in markers:
            if (parent / marker).exists():
                return parent
    raise FileNotFoundError(f"No {markers} found in {start}, 请确认仓库的根目录是否存在{WORKSPACE_MARKER}文件")

# 计算一下ROOT_DIR根目录
ROOT_DIR: Path = _find_workspace_root(Path(__file__))

# 端代码目录APP_DIR(platform这个根)
APP_DIR: Path = ROOT_DIR / "apps" / "platform"

# 共享资产(ROOT_DIR下，所有端都可以访问的文件)
DATA_DIR: Path = ROOT_DIR / "data"
MODELS_DIR: Path = DATA_DIR / "models"
RUNS_DIR : Path = DATA_DIR / "runs"

# 模型有子目录
PRETRAINED_MODELS_DIR: Path = MODELS_DIR / "pretrained"
CHECKPOINTS_DIR: Path = MODELS_DIR / "checkpoints"

# 数据集子目录
RAW_DATA_DIR: Path = DATA_DIR / "raw"

TRAIN_DIR : Path = DATA_DIR / "train"
TEST_DIR : Path = DATA_DIR / "test"
VAL_DIR : Path = DATA_DIR / "valid"

TRAIN_IMAGES_DIR: Path = TRAIN_DIR / "images"
TEST_IMAGES_DIR: Path = TEST_DIR / "images"
VAL_IMAGES_DIR: Path = VAL_DIR / "images"

TRAIN_LABELS_DIR: Path = TRAIN_DIR / "labels"
TEST_LABELS_DIR: Path = TEST_DIR / "labels"
VAL_LABELS_DIR: Path = VAL_DIR / "labels"

# 【端私有资产】只属于platform这个端的资产文件
CONFIGS_DIR: Path = APP_DIR / "configs"
LOGGING_DIR: Path = APP_DIR / "logging"
UNIT_TEST_DIR: Path = APP_DIR / "tests"

# 顶层的文档目录[共享给所有人]
DOCS_DIR: Path = ROOT_DIR / "docs"

# 工程基础设施目录
SCRIPTS_DIR: Path = ROOT_DIR / "scripts"


# 对外暴露的要初始化的目录列表
def get_dirs_to_initialize() -> List[Path]:
    """
    返回项目启动时需要确保存在的所有目录列表
    :return: 所有需要初始化的目录路径列表
    """
    return [
        DATA_DIR,
        MODELS_DIR,
        RUNS_DIR,
        PRETRAINED_MODELS_DIR,
        CHECKPOINTS_DIR,
        RAW_DATA_DIR,
        TRAIN_IMAGES_DIR,
        TEST_IMAGES_DIR,
        VAL_IMAGES_DIR,
        TRAIN_LABELS_DIR,
        TEST_LABELS_DIR,
        VAL_LABELS_DIR,
        CONFIGS_DIR,
        LOGGING_DIR,
        UNIT_TEST_DIR,
        SCRIPTS_DIR,
        DOCS_DIR,
    ]

if __name__ == "__main__":
    print(f"ROOT_DIR (workspace) = {ROOT_DIR}")
    print(f"APP_DIR (platform) = {APP_DIR}")

    print(f"需要初始化的目录共有{len(get_dirs_to_initialize())}个")
    for d in get_dirs_to_initialize():
        print(f"  - {d.relative_to(ROOT_DIR)}")