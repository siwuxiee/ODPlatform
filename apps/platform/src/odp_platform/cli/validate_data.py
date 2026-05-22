#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""CLI 入口：odp-validate"""

import argparse
import logging
import sys
from pathlib import Path

from odp_platform.common.paths import LOGGING_DIR, dataset_yaml_path
from odp_platform.common.logging_utils import get_logger

get_logger(
    base_path=LOGGING_DIR,
    log_type="validate",
    temp_log=False,
    log_level=logging.INFO,
)

from odp_platform.data_validation import validate_dataset, render_to_logger


def main():
    parser = argparse.ArgumentParser(
        description="ODPlatform 数据质检工具：检查数据集能否用于训练",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dataset", help="数据集名称 (走 configs/datasets/<name>.yaml)")
    group.add_argument("--yaml", help="直接指定 yaml 路径")
    parser.add_argument("--task", choices=["detect", "segment"], default=None,
                        help="任务类型 (不传则按 yaml.task → detect 兜底)")
    parser.add_argument("--no-report", action="store_true", help="不写 JSON 报告")
    parser.add_argument("-v", "--verbose", action="store_true", help="DEBUG 级日志")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger("odp_platform").setLevel(logging.DEBUG)

    yaml_path = Path(args.yaml) if args.yaml else dataset_yaml_path(args.dataset)

    try:
        report = validate_dataset(
            yaml_path=yaml_path,
            task_type=args.task,
            write_report=not args.no_report,
        )
    except KeyboardInterrupt:
        logger = logging.getLogger(__name__)
        logger.warning("用户中断 (Ctrl-C)")
        sys.exit(3)
    except Exception:
        logger = logging.getLogger(__name__)
        logger.exception("odp-validate 执行失败")
        sys.exit(3)

    render_to_logger(report, verbose=args.verbose)
    sys.exit(report.exit_code)


if __name__ == "__main__":
    main()
