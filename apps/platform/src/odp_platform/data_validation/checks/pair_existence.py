import logging
from pathlib import Path
from typing import Any, Dict, List

from odp_platform.common.constants import (
    PAIR_MISSING_ERROR_RATIO,
    PAIR_MISSING_WARN_RATIO,
)

from ..registry import CheckContext, CheckResult, CheckSeverity, check

logger = logging.getLogger(__name__)

DETAILS_PREVIEW_LIMIT = 20


@check("pair_existence")
def validate_pair_existence(ctx: CheckContext) -> CheckResult:
    snapshot = ctx.snapshot
    if snapshot is None:
        return CheckResult(
            name="pair_existence",
            severity=CheckSeverity.ERROR,
            summary="snapshot 未初始化，无法执行 pair_existence 检查",
            details={"error": "snapshot_is_none"},
        )

    total_images = 0
    total_missing = 0
    missing_per_split: Dict[str, int] = {}
    missing_examples: Dict[str, List[str]] = {}

    for split_name in snapshot.splits:
        images = snapshot.images_per_split.get(split_name, ())
        labels = snapshot.labels_per_split.get(split_name, ())
        label_stems = {lb.stem for lb in labels}
        missing: List[str] = []
        for img in images:
            total_images += 1
            if img.stem not in label_stems:
                total_missing += 1
                missing.append(str(img.name))

        if missing:
            missing_per_split[split_name] = len(missing)
            missing_examples[split_name] = missing[:DETAILS_PREVIEW_LIMIT]
        else:
            missing_per_split[split_name] = 0
            missing_examples[split_name] = []

    # --- 分级 ---
    if total_images == 0:
        return CheckResult(
            name="pair_existence",
            severity=CheckSeverity.WARNING,
            summary="没有图像，请检查数据集 YAML 的 path 字段是否正确指向数据目录",
            details={"total_images": 0, "total_missing": 0, "missing_ratio": 0.0},
        )

    missing_ratio = total_missing / total_images

    if missing_ratio == 0.0:
        severity = CheckSeverity.PASS
        summary = "所有图像均有对应标签文件"
    elif missing_ratio >= PAIR_MISSING_ERROR_RATIO:
        severity = CheckSeverity.ERROR
        summary = f"{total_missing}/{total_images} 图像缺失标签 ({missing_ratio:.1%})，流程可能崩了"
    elif missing_ratio >= PAIR_MISSING_WARN_RATIO:
        severity = CheckSeverity.WARNING
        summary = f"{total_missing}/{total_images} 图像缺失标签 ({missing_ratio:.1%})，可能影响精度"
    else:
        severity = CheckSeverity.INFO
        summary = f"{total_missing}/{total_images} 图像缺失标签 ({missing_ratio:.1%})，数量较少"

    details: Dict[str, Any] = {
        "total_images": total_images,
        "total_missing": total_missing,
        "missing_ratio": missing_ratio,
        "thresholds": {
            "error": PAIR_MISSING_ERROR_RATIO,
            "warn": PAIR_MISSING_WARN_RATIO,
        },
        "missing_per_split": missing_per_split,
        "missing_examples": missing_examples,
    }

    return CheckResult(
        name="pair_existence",
        severity=severity,
        summary=summary,
        details=details,
    )
