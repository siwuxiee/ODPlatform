#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @FileName  : infer.py
# @Project   : ODPlatform
# @Function  : odp-infer CLI 入口 — argparse + 装日志 handler + 调 InferService
"""odp-infer CLI 入口(镜像 odp-train).

★ 职责边界(跟 D6 CLI 完全同构):
  - 解析 argparse (把 CLI 字段变成 dict, 交给 D5 build_infer_config 合并)
  - 装文件日志 handler (业务模块只发声纪律的兑现位 — 唯一装 handler 的地方)
  - 调 InferService.predict(...) 跑推理
  - 把退出码翻译给操作系统 (0/1/130)

CLI 不做的事:
  - 不合并配置(那是 D5 的事)
  - 不解析模型/源路径(那是 service / common / frame_source 的事)
  - 不动 ultralytics、不画框(那是 service 的事)
"""
from __future__ import annotations

import argparse
import logging
import sys

from odp_platform.common.logging_utils import get_logger
from odp_platform.common.paths import LOGGING_DIR

from odp_platform.inference import InferService


# ============================================================================
# argparse
# ============================================================================

def build_parser() -> argparse.ArgumentParser:
    """构造 argparse parser. 拆出来让测试可以独立验证 CLI 表面."""
    parser = argparse.ArgumentParser(
        prog="odp-infer",
        description="YOLO 推理 — 调 D5 配置 + 帧源捕获 + ultralytics 推理 + 美化绘制",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  odp-infer --source 0                       # 摄像头
  odp-infer --source demo.mp4                # 视频
  odp-infer --source test.jpg                # 单图
  odp-infer --source ./images/               # 图片文件夹
  odp-infer --source 0 --show                # 摄像头 + 弹窗实时显示
  odp-infer --source demo.mp4 --conf 0.5     # 覆盖置信度阈值
  odp-infer --source 0 --no-viz              # 关美化, 退回 YOLO 原生绘制
  odp-infer --source demo.mp4 --no-save      # 只跑+打统计, 不落盘
  odp-infer --yaml my_infer.yaml --pipeline-yaml my_pipe.yaml
        """,
    )

    # ---- 两份配置文件 ----
    parser.add_argument(
        "--yaml", type=str, default=None,
        help="D5 infer.yaml 路径(YOLO predict 参数; 默认走 RUNTIME_CONFIGS_DIR/infer.yaml)",
    )
    parser.add_argument(
        "--pipeline-yaml", dest="pipeline_yaml", type=str, default=None,
        help="帧源+美化 infer_pipeline.yaml 路径(默认走 RUNTIME_CONFIGS_DIR/infer_pipeline.yaml)",
    )

    # ---- 推理参数(覆盖 D5 infer.yaml, 走 merger) ----
    parser.add_argument("--source",  type=str, help="输入源: 图/视频/目录/摄像头号(覆盖 yaml)")
    parser.add_argument("--model",   type=str, help="模型路径/文件名(默认走 yaml)")
    parser.add_argument("--conf",    type=float, help="置信度阈值")
    parser.add_argument("--iou",     type=float, help="NMS IoU 阈值")
    parser.add_argument("--imgsz",   type=int,   help="输入图像尺寸")
    parser.add_argument("--batch",   type=int,   help="帧批大小(一次 GPU 推理多少帧; 图片夹/视频吞吐关键, 实时摄像头设 1)")
    parser.add_argument("--device",  type=str,   help="推理设备(0/cpu/0,1)")
    parser.add_argument("--max-det", dest="max_det", type=int, help="单图最大检测数")
    parser.add_argument("--classes", type=int, nargs="+", help="只检测的类别 ID(空格分隔)")
    parser.add_argument("--experiment-name", dest="experiment_name", type=str,
                        help="实验名(进 runs/<task>_infer/<experiment_name>/)")

    # ---- show / save 也是 YOLOInferConfig 字段, 走 merger(自带溯源) ----
    parser.add_argument(
        "--show", dest="show", action="store_const", const=True, default=None,
        help="弹窗实时显示(需 GUI; 服务器/Docker 不要开)",
    )
    parser.add_argument(
        "--no-save", dest="save", action="store_const", const=False, default=None,
        help="不落盘, 只跑 + 打统计",
    )

    # ---- D8 服务层开关(service 的 keyword-only 参数) ----
    parser.add_argument(
        "--threaded", action="store_true",
        help="多线程流水线(采集/推理/美化三路并行; 摄像头/视频/RTSP 实时推荐). "
             "图片/文件夹源会自动回退顺序执行.",
    )
    parser.add_argument(
        "--warmup", dest="warmup_frames", type=int, default=0,
        help="多线程: 启动丢弃前 N 帧(摄像头预热, 帧率不稳), default 0",
    )
    parser.add_argument(
        "--window-name", dest="window_name", type=str, default="odp-infer",
        help="显示窗口标题(--show 时)",
    )
    parser.add_argument(
        "--no-viz", dest="beautify", action="store_false", default=True,
        help="关闭美化, 退回 YOLO 原生 plot() 绘制",
    )
    parser.add_argument(
        "--no-info", dest="show_info", action="store_false", default=True,
        help="不在画面上叠加信息面板(帧率/检测数等 HUD)",
    )
    parser.add_argument(
        "--no-rename-log", dest="rename_log", action="store_false", default=True,
        help="不把日志文件名改成 <output_dir>_<ts>_<model>.log 形式",
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
        log_type="infer",
        log_level=getattr(logging, log_level),
        temp_log=False,
    )


# ============================================================================
# main 入口
# ============================================================================

def main() -> int:
    """odp-infer 主入口. 返回退出码 0/1/130."""
    parser = build_parser()
    args = parser.parse_args()

    # 1. 装日志 handler (走 D2 get_logger, 唯一一次)
    _setup_logging(args.log_level)
    log = logging.getLogger("odp_platform.cli.infer")

    # 2. argparse.Namespace → dict, 过滤 None(让 D5 走默认值) + 拆出非配置字段
    #    NON_CONFIG_KEYS: 不是 YOLOInferConfig 字段的, 不能混进 cli_args(否则 D5 报 extra forbid)
    NON_CONFIG_KEYS = {
        "yaml", "pipeline_yaml", "beautify", "rename_log", "log_level",
        "threaded", "warmup_frames", "window_name", "show_info",
    }
    cli_args = {
        k: v for k, v in vars(args).items()
        if v is not None and k not in NON_CONFIG_KEYS
    }

    # 3. 调 service
    log.info(f"启动 odp-infer, CLI 字段: {list(cli_args.keys())}")
    try:
        service = InferService()
        result = service.predict(
            yaml_path=args.yaml,
            pipeline_yaml=args.pipeline_yaml,
            cli_args=cli_args,
            beautify=args.beautify,
            rename_log=args.rename_log,
            threaded=args.threaded,
            warmup_frames=args.warmup_frames,
            window_name=args.window_name,
            show_info=args.show_info,
        )
    except KeyboardInterrupt:
        log.warning("用户中断 (Ctrl+C)")
        return 130
    except Exception as e:        # service 本应 not raise, 兜底
        log.error(f"未预期异常: {e}", exc_info=True)
        return 1

    # 4. 退出码
    if result.success:
        log.info(f"✓ 推理成功. 用时 {result.infer_time:.2f}s, 输出 {result.output_dir}")
        return 0
    else:
        log.error(f"✗ 推理失败: {result.error}")
        return 1


if __name__ == "__main__":
    sys.exit(main())