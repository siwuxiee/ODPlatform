#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @FileName  : val_model.py
# @Project   : ODPlatform
# @Function  : odp-val CLI 入口 — argparse + 装日志 handler + 调 ValService
"""odp-val CLI 入口.

★ 职责边界:
  - 解析 argparse (把 CLI 字段变成 dict, 交给 D5 build_val_config 合并)
  - 装文件日志 handler (业务模块只发声纪律的兑现位 — 唯一装 handler 的地方)
  - 调 ValService.evaluate(...) 跑验证
  - 把退出码翻译给操作系统 (0/1/130)

CLI 不做的事:
  - 不合并配置(那是 D5 的事)
  - 不动 ultralytics(那是 service 的事)
"""
from __future__ import annotations

import argparse
import logging
import sys

from odp_platform.common.logging_utils import get_logger
from odp_platform.common.paths import LOGGING_DIR

from odp_platform.evaluation import ValService


# ============================================================================
# argparse
# ============================================================================

def build_parser() -> argparse.ArgumentParser:
    """构造 argparse parser. 拆出来让测试可以独立验证 CLI 表面."""
    parser = argparse.ArgumentParser(
        prog="odp-val",
        description="YOLO 验证 — 调 D5 配置 + ultralytics 验证",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  odp-val                                       # 默认 val.yaml
  odp-val --yaml my_val.yaml
  odp-val --model runs/detect_train/train/weights/best.pt --data rsod.yaml
  odp-val --split test --conf 0.5
  odp-val --device 0 --half
  odp-val --save-json --save-hybrid
  odp-val --no-rename-log
        """,
    )

    # ---- 配置文件 ----
    parser.add_argument(
        "--yaml", type=str, default=None,
        help="YAML 配置文件路径(默认走 RUNTIME_CONFIGS_DIR/val.yaml)",
    )

    # ---- 验证参数(覆盖 yaml) ----
    parser.add_argument("--model",     type=str,   help="模型路径(.pt 权重文件)")
    parser.add_argument("--data",      type=str,   help="数据集 yaml")
    parser.add_argument("--batch",     type=int,   help="batch size")
    parser.add_argument("--imgsz",     type=int,   help="输入图像尺寸")
    parser.add_argument("--device",    type=str,   help="设备(0/cpu/0,1)")
    parser.add_argument("--workers",   type=int,   help="DataLoader workers")
    parser.add_argument("--seed",      type=int,   help="随机种子")
    parser.add_argument("--project",   type=str,   help="输出根目录")
    parser.add_argument("--name",      type=str,   help="运行名(yolo 用)")
    parser.add_argument("--experiment-name", dest="experiment_name", type=str,
                        help="实验名(ODP 用, 进 runs/<task>_val/<experiment_name>/)")

    # ---- 验证专属参数(YOLOValConfig 专有) ----
    parser.add_argument("--split",     type=str,   help="数据集划分(val/test/train)")
    parser.add_argument("--conf",      type=float, help="置信度阈值")
    parser.add_argument("--iou",       type=float, help="NMS IoU 阈值")
    parser.add_argument("--max-det",   type=int,   help="每张图最大检测数")
    parser.add_argument("--half",      type=str,   help="半精度推理(true/false)")
    parser.add_argument("--plots",     type=str,   help="生成评估图表(true/false)")
    parser.add_argument("--save-json", type=str,   help="保存 COCO JSON 结果(true/false)")
    parser.add_argument("--save-hybrid", type=str, help="保存混合标签(true/false)")

    # ---- D7 开关 ----
    parser.add_argument(
        "--no-rename-log", dest="rename_log", action="store_false", default=True,
        help="不把日志文件名改成 <save_dir>_<ts>_<model>.log 形式",
    )

    # ---- 可选辅助 ----
    parser.add_argument(
        "--log-level", default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="日志级别",
    )

    return parser


# ============================================================================
# 日志 handler 装载 — 业务模块只发声, handler 唯一装的地方就在这
# ============================================================================

def _setup_logging(log_level: str) -> None:
    """调 D2 的 get_logger 给 'odp_platform' 根 logger 装上 console + file handler."""
    get_logger(
        base_path=LOGGING_DIR,
        log_type="val",
        log_level=getattr(logging, log_level),
        temp_log=False,
    )


# ============================================================================
# main 入口
# ============================================================================

def main() -> int:
    """odp-val 主入口. 返回退出码 0/1/130."""
    parser = build_parser()
    args = parser.parse_args()

    # 1. 装日志 handler (走 D2 get_logger, 唯一一次)
    _setup_logging(args.log_level)
    log = logging.getLogger("odp_platform.cli.val_model")

    # 2. argparse.Namespace → dict, 过滤 None(让 D5 走默认值) + 拆出非配置字段
    NON_CONFIG_KEYS = {
        "yaml", "rename_log", "log_level",
    }
    cli_args = {
        k: v for k, v in vars(args).items()
        if v is not None and k not in NON_CONFIG_KEYS
    }

    # 3. 调 service
    log.info(f"启动 odp-val, CLI 字段: {list(cli_args.keys())}")
    try:
        service = ValService()
        result = service.evaluate(
            yaml_path=args.yaml,
            cli_args=cli_args,
            rename_log=args.rename_log,
        )
    except KeyboardInterrupt:
        log.warning("用户中断 (Ctrl+C)")
        return 130
    except Exception as e:        # service 本应 not raise, 兜底
        log.error(f"未预期异常: {e}", exc_info=True)
        return 1

    # 4. 退出码
    if result.success:
        log.info(f"验证成功. 用时 {result.eval_time:.2f}s, 输出 {result.output_dir}")
        return 0
    else:
        log.error(f"验证失败: {result.error}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
