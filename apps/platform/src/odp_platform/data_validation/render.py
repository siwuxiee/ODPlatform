import logging
from typing import Optional

from .registry import CheckSeverity
from .report import ValidationReport

logger = logging.getLogger(__name__)


def render_to_logger(report: ValidationReport, verbose: bool = False) -> None:
    snapshot = report.snapshot
    counts = report.counts_by_severity

    # ── 第一章: 数据集摘要 ──
    logger.info("=" * 60)
    logger.info("  数据集验证报告")
    logger.info("=" * 60)
    logger.info(f"  run_id:      %s", report.run_id)
    logger.info(f"  yaml:        %s", report.yaml_path)
    logger.info(f"  task:        %s", snapshot.task_type)
    logger.info(f"  nc:          %s", snapshot.nc)
    logger.info(f"  总图像数:    %s", snapshot.total_images)
    logger.info(f"  splits:      %s", ", ".join(snapshot.splits))
    for s in snapshot.splits:
        st = snapshot.stats_per_split.get(s)
        if st:
            logger.info(f"    {s}: %s 图像, %s 有标注, %s 实例",
                        st.image_count, st.annotated_count, st.total_instances)
    if snapshot.scan_warnings:
        for w in snapshot.scan_warnings:
            logger.warning(f"  扫描警告: %s", w)
    logger.info(f"  耗时:        %.3f 秒", report.duration_seconds)
    logger.info(f"  整体级别:    %s", report.overall_severity)

    # ── 第二章: 各 check 一览 ──
    logger.info("─" * 60)
    logger.info("  check 结果一览:   ERROR=%d  WARNING=%d  INFO=%d  PASS=%d",
                counts[CheckSeverity.ERROR],
                counts[CheckSeverity.WARNING],
                counts[CheckSeverity.INFO],
                counts[CheckSeverity.PASS])

    for r in report.results:
        sev = r.severity
        if sev == CheckSeverity.PASS:
            if verbose:
                logger.debug("  [%s] %s: %s", sev, r.name, r.summary)
        elif sev == CheckSeverity.INFO:
            logger.info("  [%s] %s: %s", sev, r.name, r.summary)
        elif sev == CheckSeverity.WARNING:
            logger.warning("  [%s] %s: %s", sev, r.name, r.summary)
        else:
            logger.error("  [%s] %s: %s", sev, r.name, r.summary)

    # ── 第三章: 失败详情 ──
    failed = report.failed_results
    if failed:
        logger.info("─" * 60)
        logger.info("  失败详情 (%d 个 check):", len(failed))
        for r in failed:
            logger.info("  [%s] %s:", r.severity, r.name)
            logger.info("    summary: %s", r.summary)
            _render_details(r.name, r.details)

    logger.info("=" * 60)
    logger.info("  退出码: %d", report.exit_code)

    if report.report_path:
        logger.info("  JSON 报告: %s", report.report_path)


def _render_details(name: str, details: dict, indent: int = 2) -> None:
    prefix = " " * (indent * 2)
    for k, v in details.items():
        if k == "problems":
            for problem in v:
                logger.info("%s- %s", prefix, problem)
        elif k == "error_kinds":
            logger.info("%s%s:", prefix, k)
            for ek, count in v.items():
                if count > 0:
                    logger.info("%s  - %s: %d", prefix, ek, count)
        elif k == "errors_preview":
            logger.info("%s%s (前 %d 条):", prefix, k, len(v))
            for err in v:
                logger.info("%s  - [%s] L%s: %s", prefix, err.get("file", "?"), err.get("line", "?"), err.get("message", ""))
        elif k == "overlaps":
            for pair_key, pair_data in v.items():
                logger.info("%s%s: %d 个重复 stem", prefix, pair_key, pair_data.get("count", 0))
                stems = pair_data.get("stems", [])
                if stems:
                    logger.info("%s  前几条: %s", prefix, ", ".join(stems[:5]))
        elif k == "missing_per_split":
            for split_name, count in v.items():
                logger.info("%s%s: %d 缺失", prefix, split_name, count)
        elif k == "missing_examples":
            for split_name, examples in v.items():
                if examples:
                    logger.info("%s%s 示例: %s", prefix, split_name, ", ".join(examples[:5]))
        elif k == "thresholds":
            logger.info("%s%s: error=%.0f%% warn=%.0f%%", prefix, k, v.get("error", 0) * 100, v.get("warn", 0) * 100)
        elif k == "scan_warnings":
            pass
        elif isinstance(v, (int, float, str)):
            if k not in ("total_images", "total_missing", "missing_ratio", "total_lines", "total_errors", "total_duplicates", "task_type", "yaml_path", "splits"):
                logger.info("%s%s: %s", prefix, k, v)
