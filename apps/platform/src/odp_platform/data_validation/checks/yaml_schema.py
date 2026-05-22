import logging
from pathlib import Path
from typing import Any, Dict, List

import yaml

from ..registry import CheckContext, CheckResult, CheckSeverity, check

logger = logging.getLogger(__name__)


@check("yaml_schema")
def validate_yaml_schema(ctx: CheckContext) -> CheckResult:
    yaml_path: Path = ctx.yaml_path

    # --- 前置错误: 文件不存在 ---
    if not yaml_path.exists():
        return CheckResult(
            name="yaml_schema",
            severity=CheckSeverity.ERROR,
            summary=f"yaml 文件不存在: {yaml_path}",
            details={"yaml_path": str(yaml_path), "problems": ["file_not_found"]},
        )

    # --- 前置错误: 解析失败 ---
    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        return CheckResult(
            name="yaml_schema",
            severity=CheckSeverity.ERROR,
            summary=f"yaml 解析失败: {e}",
            details={"yaml_path": str(yaml_path), "problems": ["parse_error"], "error": str(e)},
        )
    except OSError as e:
        return CheckResult(
            name="yaml_schema",
            severity=CheckSeverity.ERROR,
            summary=f"无法读取 yaml 文件: {e}",
            details={"yaml_path": str(yaml_path), "problems": ["read_error"], "error": str(e)},
        )

    # --- 前置错误: 顶层不是 dict ---
    if not isinstance(data, dict):
        return CheckResult(
            name="yaml_schema",
            severity=CheckSeverity.ERROR,
            summary="yaml 顶层不是 dict",
            details={"yaml_path": str(yaml_path), "problems": ["top_level_not_dict"]},
        )

    # --- 字段一致性: 收集所有问题 ---
    problems: List[str] = []

    # nc 检查
    nc = data.get("nc")
    if nc is None:
        problems.append("缺少 'nc' 字段")
    elif not isinstance(nc, int) or nc <= 0:
        problems.append(f"'nc' 必须为正整数，当前: {nc}")

    # names 检查
    names = data.get("names")
    if names is None:
        problems.append("缺少 'names' 字段")
    elif isinstance(names, list):
        if not all(isinstance(n, str) and n for n in names):
            problems.append("'names' 为 list 时所有元素必须为非空字符串")
        elif nc is not None and isinstance(nc, int) and nc > 0:
            if len(names) != nc:
                problems.append(f"nc ({nc}) 跟 names 长度 ({len(names)}) 不一致")
    elif isinstance(names, dict):
        invalid_entries = []
        for k, v in names.items():
            if not isinstance(k, int):
                invalid_entries.append(f"键 {k!r} 不是 int")
            if not isinstance(v, str) or not v:
                invalid_entries.append(f"键 {k!r} 对应值 {v!r} 不是有效名称")
        if invalid_entries:
            problems.append(f"'names' 为 dict 时存在问题: {'; '.join(invalid_entries)}")
        if nc is not None and isinstance(nc, int) and nc > 0 and not invalid_entries:
            if len(names) != nc:
                problems.append(f"nc ({nc}) 跟 names 长度 ({len(names)}) 不一致")
    else:
        problems.append(f"'names' 类型不合法 ({type(names).__name__})，应为 list 或 dict")

    if problems:
        return CheckResult(
            name="yaml_schema",
            severity=CheckSeverity.ERROR,
            summary=f"yaml schema 存在 {len(problems)} 个问题",
            details={"yaml_path": str(yaml_path), "problems": problems},
        )

    return CheckResult(
        name="yaml_schema",
        severity=CheckSeverity.PASS,
        summary="yaml schema 校验通过",
        details={"yaml_path": str(yaml_path), "nc": nc, "names_count": len(names) if hasattr(names, '__len__') else None},
    )
