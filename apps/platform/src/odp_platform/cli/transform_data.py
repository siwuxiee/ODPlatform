#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""CLI 入口：odp-transform"""

import argparse
import sys
import logging
from pathlib import Path
import tempfile            # 新增引入
import contextlib          # 新增引入

# ── 日志初始化（必须在其他 ODP 导入之前，确保根 logger 最先装配） ─
from odp_platform.common.paths import LOGGING_DIR
from odp_platform.common.logging_utils import get_logger

get_logger(
    base_path=LOGGING_DIR,
    log_type="transform",   # 日志目录：logging/transform/
    temp_log=False,
    log_level=logging.INFO,
)

from odp_platform.common.paths import (
    DATA_RAW_DIR,
    CONFIG_DATASETS_DIR,
)
from odp_platform.data_pipeline import list_capabilities, Orchestrator


def main():
    parser = argparse.ArgumentParser(
        description="ODPlatform 数据转换工具：将原始数据集转化为 YOLO 格式并生成划分配置",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__build_capabilities_epilog(),
    )

    parser.add_argument("--dataset", required=True, help="数据集名称")
    parser.add_argument("--format", default="pascal_voc", help="原始格式")
    parser.add_argument("--raw-dir", default=None, help="原始数据集根目录")
    parser.add_argument("--output-dir", default=None, help="转换后的标准化存放基目录")
    parser.add_argument("--config-dir", default=None, help="生成的 data.yaml 存放目录")
    parser.add_argument("--classes", default=None, help="逗号分隔类别列表")
    parser.add_argument("--task", default="detect", choices=["detect", "segment"])
    parser.add_argument("--train-ratio", type=float, default=0.7)
    parser.add_argument("--val-ratio", type=float, default=0.15)
    parser.add_argument("--test-ratio", type=float, default=0.15)
    parser.add_argument("--random-state", type=int, default=42)

    args = parser.parse_args()

    dataset_name = args.dataset
    raw_dir = Path(args.raw_dir) if args.raw_dir else DATA_RAW_DIR / dataset_name
    if not raw_dir.exists():
        print(f"错误：原始数据集目录不存在：{raw_dir}", file=sys.stderr)
        sys.exit(1)

    # 替换原本的 base_out 定义逻辑：
    with contextlib.ExitStack() as stack:
        if args.output_dir:
            # 如果用户明确指定了保存中间产物的目录，则使用用户的路径
            base_out = Path(args.output_dir)
        else:
            # 如果没有指定，则开启一个用完即焚的系统临时目录，避免生成 datasets 文件夹
            temp_dir = stack.enter_context(tempfile.TemporaryDirectory())
            base_out = Path(temp_dir)

        output_images = base_out / "images"
        output_labels = base_out / "labels"

        config_yaml = (
            Path(args.config_dir)
            if args.config_dir
            else CONFIG_DATASETS_DIR / f"{dataset_name}.yaml"
        )

        classes_list = None
        if args.classes:
            classes_list = [c.strip() for c in args.classes.split(",") if c.strip()]

        orchestrator = Orchestrator(
            dataset_name=dataset_name,
            format_name=args.format,
            raw_data_dir=raw_dir,
            output_images_dir=output_images,
            output_labels_dir=output_labels,
            config_yaml_path=config_yaml,
            train_ratio=args.train_ratio,
            val_ratio=args.val_ratio,
            test_ratio=args.test_ratio,
            random_state=args.random_state,
            user_classes=classes_list,
            task=args.task,
        )

        try:
            orchestrator.run()
        except Exception as e:
            print(f"流水线执行失败：{e}", file=sys.stderr)
            sys.exit(2)

        print(f"成功！配置文件已生成：{config_yaml}")


def __build_capabilities_epilog() -> str:
    try:
        caps = list_capabilities()
        lines = ["当前支持的格式及任务："]
        for fmt, tasks in caps.items():
            lines.append(f"  {fmt:<12} → {', '.join(tasks)}")
        return "\n".join(lines)
    except Exception:
        return "（未能加载能力矩阵）"


if __name__ == "__main__":
    main()