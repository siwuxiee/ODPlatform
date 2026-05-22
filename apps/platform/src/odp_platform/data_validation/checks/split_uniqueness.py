import logging
from itertools import combinations
from pathlib import Path
from typing import Any, Dict, List, Tuple

from ..registry import CheckContext, CheckResult, CheckSeverity, check

logger = logging.getLogger(__name__)

OVERLAP_PREVIEW_LIMIT = 20


@check("split_uniqueness")
def validate_split_uniqueness(ctx: CheckContext) -> CheckResult:
    snapshot = ctx.snapshot
    if snapshot is None:
        return CheckResult(
            name="split_uniqueness",
            severity=CheckSeverity.ERROR,
            summary="snapshot 未初始化，无法执行 split_uniqueness 检查",
            details={"error": "snapshot_is_none"},
        )

    splits = list(snapshot.splits)
    if len(splits) < 2:
        return CheckResult(
            name="split_uniqueness",
            severity=CheckSeverity.PASS,
            summary="split 数量不足 2 个，无需检查唯一性",
            details={"splits": splits, "total_duplicates": 0, "overlaps": {}},
        )

    stems_per_split: Dict[str, set] = {}
    for s in splits:
        stems_per_split[s] = {img.stem for img in snapshot.images_per_split.get(s, ())}

    total_duplicates = 0
    overlaps: Dict[str, Dict[str, Any]] = {}

    for s1, s2 in combinations(splits, 2):
        common = stems_per_split[s1] & stems_per_split[s2]
        if common:
            total_duplicates += len(common)
            overlap_key = f"{s1} ∩ {s2}"
            preview = sorted(common)[:OVERLAP_PREVIEW_LIMIT]
            overlaps[overlap_key] = {
                "count": len(common),
                "stems": preview,
            }

    if total_duplicates > 0:
        severity = CheckSeverity.ERROR
        pair_count = len(overlaps)
        summary = f"发现 {total_duplicates} 个重复图像 stem 跨 {pair_count} 对 split（数据泄露）"
    else:
        severity = CheckSeverity.PASS
        summary = "所有 split 之间图像 stem 无重复"

    return CheckResult(
        name="split_uniqueness",
        severity=severity,
        summary=summary,
        details={
            "splits": splits,
            "total_duplicates": total_duplicates,
            "overlaps": overlaps,
        },
    )
