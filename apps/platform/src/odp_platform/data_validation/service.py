import json
import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from odp_platform.common.performance_utils import time_it
from odp_platform.common.system_utils import log_device_info

from .registry import CheckContext, CheckEntry, CheckResult, CheckSeverity, get_all_checks
from .report import ValidationReport
from .snapshot import build_snapshot

logger = logging.getLogger(__name__)


def _safe_run_one(entry: CheckEntry, ctx: CheckContext) -> CheckResult:
    try:
        return entry.func(ctx)
    except Exception as e:
        logger.error("check '%s' 抛出未预期异常: %s", entry.name, e, exc_info=True)
        return CheckResult(
            name=entry.name,
            severity=CheckSeverity.ERROR,
            summary=f"check 执行异常: {e}",
            details={"exception_type": type(e).__name__, "exception_message": str(e)},
        )


@time_it(name="run_all_checks")
def run_all_checks(ctx: CheckContext) -> List[CheckResult]:
    entries = get_all_checks()
    results: List[CheckResult] = []
    for entry in entries:
        logger.info("正在执行 check: %s", entry.name)
        result = _safe_run_one(entry, ctx)
        results.append(result)
    return results


def validate_dataset(
    yaml_path: Path,
    task_type: Optional[str] = None,
    run_id: Optional[str] = None,
    run_dir: Optional[Path] = None,
    write_report: bool = True,
) -> ValidationReport:
    from odp_platform.common.paths import validation_run_dir

    if run_id is None:
        run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8]

    if run_dir is None:
        run_dir = validation_run_dir(run_id)

    run_dir.mkdir(parents=True, exist_ok=True)

    started_at = datetime.now(timezone.utc)
    started_at_iso = started_at.isoformat()
    t0 = time.perf_counter()

    log_device_info(logger)

    snapshot = build_snapshot(yaml_path, task_type=task_type)

    ctx = CheckContext(yaml_path=yaml_path, snapshot=snapshot)

    results = run_all_checks(ctx)

    duration_seconds = time.perf_counter() - t0

    report = ValidationReport(
        run_id=run_id,
        yaml_path=yaml_path,
        snapshot=snapshot,
        results=results,
        duration_seconds=duration_seconds,
        started_at_iso=started_at_iso,
        run_dir=run_dir,
    )

    if write_report and report.report_path:
        report.report_path.write_text(
            json.dumps(report.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("JSON 报告已写入: %s", report.report_path)

    return report
