import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple

from odp_platform.common.constants import Task

from ..registry import CheckContext, CheckResult, CheckSeverity, check

logger = logging.getLogger(__name__)

FIELD_COUNT_MISMATCH = "field_count_mismatch"
PARSE_ERROR = "parse_error"
CLASS_ID_OUT_OF_RANGE = "class_id_out_of_range"
COORD_OUT_OF_RANGE = "coord_out_of_range"
POLYGON_TOO_FEW_POINTS = "polygon_too_few_points"

ERRORS_PREVIEW_LIMIT = 20


@check("label_format")
def validate_label_format(ctx: CheckContext) -> CheckResult:
    snapshot = ctx.snapshot
    if snapshot is None or snapshot.nc is None:
        return CheckResult(
            name="label_format",
            severity=CheckSeverity.INFO,
            summary="nc 未确定，跳过 label_format (yaml_schema 应已报错)",
            details={"reason": "nc_is_none"},
        )

    task_type = snapshot.task_type
    nc = snapshot.nc
    total_lines = 0
    total_errors = 0
    error_kinds: Dict[str, int] = {
        FIELD_COUNT_MISMATCH: 0,
        PARSE_ERROR: 0,
        CLASS_ID_OUT_OF_RANGE: 0,
        COORD_OUT_OF_RANGE: 0,
        POLYGON_TOO_FEW_POINTS: 0,
    }
    errors_preview: List[Dict[str, Any]] = []

    for split_name in snapshot.splits:
        labels = snapshot.labels_per_split.get(split_name, ())
        for label_path in labels:
            try:
                lines = label_path.read_text(encoding="utf-8").splitlines()
            except OSError:
                continue

            for line_no, line in enumerate(lines, start=1):
                line = line.strip()
                if not line:
                    continue
                total_lines += 1

                err = _check_line(line, line_no, label_path.name, task_type, nc)
                if err:
                    total_errors += 1
                    error_kinds[err["kind"]] = error_kinds.get(err["kind"], 0) + 1
                    if len(errors_preview) < ERRORS_PREVIEW_LIMIT:
                        errors_preview.append(err)

    summary: str
    if total_errors == 0:
        severity = CheckSeverity.PASS
        summary = f"label_format 通过 ({total_lines} 行)"
    else:
        severity = CheckSeverity.ERROR
        summary = f"label_format 发现 {total_errors}/{total_lines} 行格式错误"

    return CheckResult(
        name="label_format",
        severity=severity,
        summary=summary,
        details={
            "task_type": task_type,
            "total_lines": total_lines,
            "total_errors": total_errors,
            "error_kinds": error_kinds,
            "errors_preview": errors_preview,
        },
    )


def _check_line(
    line: str, line_no: int, filename: str, task_type: str, nc: int
) -> Dict[str, Any] | None:
    parts = line.split()
    try:
        values = [float(x) for x in parts]
    except ValueError:
        return {
            "file": filename,
            "line": line_no,
            "kind": PARSE_ERROR,
            "message": f"无法解析为数字: {line!r}",
        }

    if task_type == Task.DETECT:
        if len(values) != 5:
            return {
                "file": filename,
                "line": line_no,
                "kind": FIELD_COUNT_MISMATCH,
                "message": f"期望 5 字段，实际 {len(values)} 字段",
            }
        cls_id = int(values[0])
        if cls_id < 0 or cls_id >= nc:
            return {
                "file": filename,
                "line": line_no,
                "kind": CLASS_ID_OUT_OF_RANGE,
                "message": f"class_id {cls_id} 不在 [0, {nc})",
            }
        for i, coord in enumerate(values[1:], start=1):
            if coord < 0.0 or coord > 1.0:
                return {
                    "file": filename,
                    "line": line_no,
                    "kind": COORD_OUT_OF_RANGE,
                    "message": f"坐标[{i}]={coord} 不在 [0, 1]",
                }
    else:
        # segment
        if len(values) < 7:
            return {
                "file": filename,
                "line": line_no,
                "kind": FIELD_COUNT_MISMATCH,
                "message": f"segment 至少需要 7 字段 (cls + >=3 坐标对)，实际 {len(values)}",
            }
        if len(values) % 2 != 1:
            return {
                "file": filename,
                "line": line_no,
                "kind": FIELD_COUNT_MISMATCH,
                "message": f"segment 字段数必须为奇数 (cls + 2N)，实际 {len(values)}",
            }
        n_points = (len(values) - 1) // 2
        if n_points < 3:
            return {
                "file": filename,
                "line": line_no,
                "kind": POLYGON_TOO_FEW_POINTS,
                "message": f"segment 多边形至少 3 个点，实际 {n_points}",
            }
        cls_id = int(values[0])
        if cls_id < 0 or cls_id >= nc:
            return {
                "file": filename,
                "line": line_no,
                "kind": CLASS_ID_OUT_OF_RANGE,
                "message": f"class_id {cls_id} 不在 [0, {nc})",
            }
        for i, coord in enumerate(values[1:], start=1):
            if coord < 0.0 or coord > 1.0:
                return {
                    "file": filename,
                    "line": line_no,
                    "kind": COORD_OUT_OF_RANGE,
                    "message": f"坐标[{i}]={coord} 不在 [0, 1]",
                }

    return None
