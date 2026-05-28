#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @FileName  : pipeline_config.py
# @Project   : ODPlatform
# @Function  : 读取 infer_pipeline.yaml(帧源+美化) — D5 管不到的那半边配置
"""帧源捕获 + 美化 的配置读取 helper.

★ 核心纪律: 不重新发明校验. 这个 helper 只做"yaml → 子字典 → 喂给现成 pydantic 模型":
  - camera 块  → frame_source.CameraConfig(**...)   (extra=forbid, 自带校验)
  - style 块   → 透传给 visualization.DrawStyle.from_image_size(**...) (拿到帧尺寸后才构造)
  - 颜色 list  → tuple (BGR), 因为美化模块吃 tuple

跟 D5 的关系: D5 的 infer.yaml 管 YOLO predict 参数(build_infer_config 读),
这份 infer_pipeline.yaml 管帧源+美化, 两份互不干涉. service 阶段 1 各读各的再捏一起.

文件缺失不算错误 —— 用默认值(美化开启、无中文映射、摄像头走 CameraConfig 默认),
打一条 warning 即可. 基本版只要有模型 + 源就能跑, pipeline yaml 是锦上添花.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


def _to_bgr_tuple(value: Any) -> tuple[int, int, int]:
    """yaml 里颜色是 list [B,G,R], 美化模块吃 tuple, 转一下."""
    if isinstance(value, (list, tuple)) and len(value) == 3:
        return (int(value[0]), int(value[1]), int(value[2]))
    raise ValueError(f"颜色必须是 3 元素的 [B, G, R], 收到: {value!r}")


@dataclass
class PipelineConfig:
    """帧源 + 美化 配置的解析结果(纯数据, 不含行为)."""

    # ---- 帧源 ----
    camera_raw: dict[str, Any] = field(default_factory=dict)   # 原始 camera 子字典, 延迟构造 CameraConfig

    # ---- 美化 ----
    viz_enabled: bool = True
    use_label_mapping: bool = True
    label_mapping: dict[str, str] = field(default_factory=dict)
    color_mapping: dict[str, tuple[int, int, int]] = field(default_factory=dict)
    default_color: tuple[int, int, int] = (0, 255, 0)
    font_path: str | None = None
    style_overrides: dict[str, Any] = field(default_factory=dict)   # 透传给 DrawStyle.from_image_size

    # ---- 溯源 ----
    source_path: Path | None = None   # 这份配置实际来自哪个文件(None=用了默认)

    def build_camera_config(self):
        """把 camera 子字典构造成 frame_source.CameraConfig.

        摄像头源才需要; 视频/图片源传 None 即可. 字段拼错这里会抛 ValidationError(fail-fast).
        返回 None 表示没配 camera 块(走 CameraConfig 默认值).
        """
        if not self.camera_raw:
            return None
        # 延迟 import: 让 frame_source 的搬迁位置变化不击穿本模块的 import 期
        from odp_platform.frame_source import CameraConfig
        return CameraConfig(**self.camera_raw)

    def to_audit(self) -> dict[str, Any]:
        """给 odp_audit.json 留一份帧源+美化配置的快照."""
        return {
            "source_path": str(self.source_path) if self.source_path else None,
            "camera": self.camera_raw or None,
            "visualization": {
                "enabled": self.viz_enabled,
                "use_label_mapping": self.use_label_mapping,
                "label_mapping": self.label_mapping or None,
                "color_mapping": {k: list(v) for k, v in self.color_mapping.items()} or None,
                "default_color": list(self.default_color),
                "font_path": self.font_path,
                "style": self.style_overrides or None,
            },
        }


def load_pipeline_config(yaml_path: str | Path | None = None) -> PipelineConfig:
    """读取 infer_pipeline.yaml → PipelineConfig.

    Args:
        yaml_path: 文件路径. None → RUNTIME_CONFIGS_DIR/infer_pipeline.yaml.
                   文件不存在 → 返回全默认的 PipelineConfig + 一条 warning(不抛).

    Returns:
        PipelineConfig. 永不抛文件不存在异常; 但 camera/style 字段非法会在
        后续构造 CameraConfig / DrawStyle 时由那两个 pydantic 模型抛 ValidationError.
    """
    from odp_platform.common.paths import RUNTIME_CONFIGS_DIR

    if yaml_path is None:
        path = RUNTIME_CONFIGS_DIR / "infer_pipeline.yaml"
    else:
        p = Path(yaml_path)
        # 跟 D5 的 yaml 解析一致: 裸文件名(无目录分量)在 RUNTIME_CONFIGS_DIR 下找;
        # 带路径或绝对路径则原样使用. 这样 `--pipeline-yaml infer_pipeline.yaml`
        # 不会被当成 CWD 相对路径而找不到(之前那条 warning 的原因).
        path = p if (p.is_absolute() or str(p.parent) != ".") else RUNTIME_CONFIGS_DIR / p

    if not path.exists():
        logger.warning(
            f"未找到帧源+美化配置 {path}, 使用默认(美化开启、无中文映射、摄像头默认参数). "
            f"如需自定义请创建该文件或用 odp-infer --pipeline-yaml 指定."
        )
        return PipelineConfig()

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    fs = raw.get("frame_source") or {}
    vz = raw.get("visualization") or {}

    color_mapping = {
        str(k): _to_bgr_tuple(v) for k, v in (vz.get("color_mapping") or {}).items()
    }
    default_color = _to_bgr_tuple(vz["default_color"]) if vz.get("default_color") else (0, 255, 0)

    return PipelineConfig(
        camera_raw=fs.get("camera") or {},
        viz_enabled=bool(vz.get("enabled", True)),
        use_label_mapping=bool(vz.get("use_label_mapping", True)),
        label_mapping={str(k): str(v) for k, v in (vz.get("label_mapping") or {}).items()},
        color_mapping=color_mapping,
        default_color=default_color,
        font_path=vz.get("font_path"),
        style_overrides=vz.get("style") or {},
        source_path=path,
    )
