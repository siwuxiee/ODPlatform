#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @FileName  : service.py
# @Project   : ODPlatform
# @Function  : ValService — 编排 D5 配置 + ultralytics 验证
"""验证服务编排器.

★ 核心纪律: 不重新发明 D5 / D2 已有的轮子. 这个 service 内部:
  - 不写 YAMLLoader / CLILoader / ConfigMerger 调用 (走 build_val_config)
  - 不配 logging handler / 不感知 FileHandler 细节
    (handler 由 D2 logging_utils.get_logger() 在 CLI 入口装好)

验证方式:
  grep "YAMLLoader\\|CLILoader\\|ConfigMerger" service.py
  → 应该没有任何输出. 子系统边界清晰的硬指标.
"""
from __future__ import annotations

import json
import logging
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from ultralytics import YOLO

from odp_platform.common.config_log import log_effective_config, log_override_chains
from odp_platform.common.dataset_path import resolve_dataset_path
from odp_platform.common.log_rename import rename_log_to_save_dir, add_model_to_log_name
from odp_platform.common.model_path import resolve_model_path
from odp_platform.common.paths import DATA_DIR, RUNS_DIR
from odp_platform.common.result import TrainMetrics, log_train_metrics
from odp_platform.common.system_utils import log_device_info
from odp_platform.runtime_config import build_val_config

logger = logging.getLogger(__name__)


def _find_project_log_path() -> Path | None:
    """从 D2 'odp_platform' 根 logger 找 FileHandler 的实际文件路径.

    只读检查, 不操作 handler. 给 audit JSON 用.
    """
    root = logging.getLogger("odp_platform")
    for h in root.handlers:
        if isinstance(h, logging.FileHandler):
            return Path(h.baseFilename)
    return None


@dataclass(frozen=True)
class ValResult:
    """评估结果一次性快照."""
    success:     bool
    output_dir:  Path
    metrics:     dict[str, float] = field(default_factory=dict)
    eval_time:   float | None = None
    error:       str | None = None
    audit_path:  Path | None = None
    log_path:    Path | None = None


class ValService:
    """YOLO 验证流程编排."""

    def __init__(self) -> None:
        """__init__ 不接任何参数 — 配置都通过 evaluate() 传."""
        pass

    def evaluate(
        self,
        yaml_path: str | Path | None = None,
        cli_args: dict[str, Any] | None = None,
        *,
        rename_log: bool = True,
    ) -> ValResult:
        """跑一次完整验证."""
        start = datetime.now()
        output_dir: Path | None = None

        try:
            # ============================================================
            # 阶段 1: 配置加载 (D5 接口承诺兑现, 一行)
            # ============================================================
            config, merger = build_val_config(
                yaml_path=yaml_path,
                cli_args=cli_args,
            )

            # ============================================================
            # 阶段 2: 上下文日志 (D2 系统快照 + D5 字段溯源)
            # ============================================================
            logger.info("=" * 60)
            logger.info(f"开始 YOLO 验证 (task={config.task})".center(60))
            logger.info("=" * 60)

            raw_model = config.model or "yolo11n.pt"
            raw_data = config.data
            logger.info(f"任务类型:    {config.task}")
            logger.info(f"数据集(声明): {raw_data}")
            data_path = resolve_dataset_path(raw_data)
            logger.info(f"数据集(解析): {data_path}")
            logger.info(f"模型(声明):  {raw_model}")
            model_path = resolve_model_path(raw_model)
            logger.info(f"模型(解析):  {model_path}")

            model_stem = Path(raw_model).stem
            add_model_to_log_name(model_stem)

            # D2 系统快照
            log_device_info(logger)

            # D5 字段溯源
            log_effective_config(config, merger, logger=logger)
            log_override_chains(config, merger, logger=logger)

            # ============================================================
            # 阶段 3: 加载模型
            # ============================================================
            model = YOLO(str(model_path))

            # ============================================================
            # 阶段 4: 执行验证 (ultralytics)
            # ============================================================
            with open(data_path, encoding="utf-8") as f:
                ds_yaml = yaml.safe_load(f)
            ds_yaml["path"] = str(DATA_DIR.resolve())
            tmp_yaml = tempfile.NamedTemporaryFile(
                mode="w", suffix=".yaml", delete=False, encoding="utf-8"
            )
            yaml.safe_dump(ds_yaml, tmp_yaml, allow_unicode=True)
            tmp_yaml.close()

            yolo_kwargs = config.to_ultralytics_kwargs()
            yolo_kwargs["data"] = tmp_yaml.name
            yolo_kwargs["model"] = str(model_path)
            yolo_kwargs.setdefault("project", str(RUNS_DIR / f"{config.task}_val"))

            logger.info("=" * 60)
            logger.info("启动验证".center(60))
            logger.info("=" * 60)
            logger.info(f"输出目录(project): {yolo_kwargs['project']}")

            val_results = model.val(**yolo_kwargs)
            output_dir = Path(val_results.save_dir)

            # ============================================================
            # 阶段 5: 结果指标
            # ============================================================
            logger.info("=" * 60)
            logger.info("验证完成".center(60))
            logger.info("=" * 60)
            metrics = TrainMetrics.from_yolo_results(val_results)
            log_train_metrics(metrics, logger=logger)

            # ============================================================
            # 阶段 6: 整理输出 (日志改名)
            # ============================================================
            if rename_log:
                rename_log_to_save_dir(output_dir, model_stem)

            # ============================================================
            # 阶段 7: 审计快照
            # ============================================================
            audit_path = output_dir / "odp_audit.json"
            log_path = _find_project_log_path()
            try:
                audit_payload = {
                    "config":  config.to_audit_snapshot(),
                    "merger":  merger.to_audit_log(),
                    "metrics": metrics.to_dict(),
                    "result_summary": {
                        "eval_time_sec": (datetime.now() - start).total_seconds(),
                        "log_path": str(log_path) if log_path else None,
                    },
                }
                audit_path.write_text(
                    json.dumps(audit_payload, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                logger.info(f"审计快照: {audit_path}")
            except OSError as e:
                logger.warning(f"写审计快照失败(不影响评估结果): {e}")
                audit_path = None

            # ============================================================
            # 收尾 — ValResult
            # ============================================================
            eval_time = (datetime.now() - start).total_seconds()

            logger.info("=" * 60)
            logger.info(f"验证总耗时: {eval_time:.2f} 秒")
            logger.info(f"输出目录:   {output_dir}")
            if log_path:
                logger.info(f"本次日志:   {log_path}")
            logger.info("=" * 60)

            return ValResult(
                success=True,
                output_dir=output_dir,
                metrics=metrics.overall,
                eval_time=eval_time,
                audit_path=audit_path,
                log_path=log_path,
            )

        # =====================================================================
        # 顶层异常拦截 — 永不抛, 打包成 ValResult.error
        # =====================================================================
        except Exception as e:
            logger.error(f"验证失败: {e}", exc_info=True)
            eval_time = (datetime.now() - start).total_seconds()
            return ValResult(
                success=False,
                output_dir=output_dir or Path("unknown"),
                metrics={},
                eval_time=eval_time,
                error=str(e),
                log_path=_find_project_log_path(),
            )


def val_yolo(
    yaml_path: str | Path | None = None,
    cli_args: dict[str, Any] | None = None,
    *,
    rename_log: bool = True,
) -> ValResult:
    """一行启动验证 — 风格跟 D5 build_val_config 一致."""
    service = ValService()
    return service.evaluate(
        yaml_path=yaml_path,
        cli_args=cli_args,
        rename_log=rename_log,
    )
