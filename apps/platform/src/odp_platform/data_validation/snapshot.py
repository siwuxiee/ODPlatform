import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from odp_platform.common.constants import (
    IMAGE_EXTENSIONS,
    SPLIT_TRAIN,
    SPLIT_VAL,
    SPLIT_TEST,
    Task,
)
from odp_platform.common.performance_utils import time_it

logger = logging.getLogger(__name__)


def _list_images(directory: Path) -> List[Path]:
    if not directory.is_dir():
        return []
    result: List[Path] = []
    for candidate in directory.iterdir():
        if not candidate.is_file():
            continue
        suffix_lower = candidate.suffix.lower()
        suffix_upper = candidate.suffix.upper()
        if suffix_lower in IMAGE_EXTENSIONS or suffix_upper in IMAGE_EXTENSIONS:
            result.append(candidate)
    return sorted(set(result))


def _count_annotated_and_instances(labels: Tuple[Path, ...]) -> Tuple[int, int]:
    annotated = 0
    instances = 0
    for lb in labels:
        try:
            text = lb.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if text:
            annotated += 1
            instances += len(text.splitlines())
    return annotated, instances


@dataclass(frozen=True)
class SplitStats:
    image_count: int
    annotated_count: int
    total_instances: int


@dataclass(frozen=True)
class DatasetSnapshot:
    yaml_path: Path
    yaml_data: Dict[str, Any]
    yaml_load_error: Optional[str]
    data_root: Path
    nc: Optional[int]
    class_names: Tuple[str, ...]
    task_type: str
    images_per_split: Dict[str, Tuple[Path, ...]]
    labels_per_split: Dict[str, Tuple[Path, ...]]
    stats_per_split: Dict[str, SplitStats]
    scan_warnings: Tuple[str, ...]

    @property
    def splits(self) -> Tuple[str, ...]:
        ordered = []
        for s in (SPLIT_TRAIN, SPLIT_VAL, SPLIT_TEST):
            if s in self.images_per_split:
                ordered.append(s)
        return tuple(ordered)

    @property
    def total_images(self) -> int:
        return sum(len(v) for v in self.images_per_split.values())


@time_it(name="build_snapshot")
def build_snapshot(yaml_path: Path) -> DatasetSnapshot:
    yaml_data: Dict[str, Any] = {}
    yaml_load_error: Optional[str] = None

    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f) or {}
        if not isinstance(yaml_data, dict):
            yaml_load_error = "yaml 顶层不是 dict"
            yaml_data = {}
    except yaml.YAMLError as e:
        yaml_load_error = f"yaml 解析失败: {e}"
    except OSError as e:
        yaml_load_error = f"无法读取 yaml: {e}"

    # --- data_root ---
    yaml_dir = yaml_path.parent
    raw_path = yaml_data.get("path", "")
    if raw_path:
        candidate = (yaml_dir / raw_path).resolve()
        if candidate.is_dir():
            data_root = candidate
        else:
            data_root = yaml_dir
    else:
        data_root = yaml_dir

    # --- nc / class_names ---
    nc: Optional[int] = None
    class_names: Tuple[str, ...] = ()
    raw_nc = yaml_data.get("nc")
    if isinstance(raw_nc, int) and raw_nc > 0:
        nc = raw_nc
    raw_names = yaml_data.get("names")
    if isinstance(raw_names, list):
        class_names = tuple(str(n) for n in raw_names if n)
    elif isinstance(raw_names, dict):
        sorted_items = sorted((int(k), str(v)) for k, v in raw_names.items() if v)
        class_names = tuple(v for _, v in sorted_items)

    # --- task_type ---
    task_type = yaml_data.get("task", Task.DETECT)
    if task_type not in (Task.DETECT, Task.SEGMENT):
        task_type = Task.DETECT

    # --- scan splits ---
    warnings: List[str] = []
    images_per_split: Dict[str, Tuple[Path, ...]] = {}
    labels_per_split: Dict[str, Tuple[Path, ...]] = {}
    stats_per_split: Dict[str, SplitStats] = {}

    for split_name in (SPLIT_TRAIN, SPLIT_VAL, SPLIT_TEST):
        split_rel = yaml_data.get(split_name, "")
        if not split_rel:
            continue
        split_dir = (data_root / split_rel).resolve()
        if not split_dir.is_dir():
            warnings.append(f"{split_name} 目录不存在: {split_dir}")
            images_per_split[split_name] = ()
            labels_per_split[split_name] = ()
            stats_per_split[split_name] = SplitStats(image_count=0, annotated_count=0, total_instances=0)
            continue

        images = _list_images(split_dir)
        images_tuple = tuple(images)

        label_paths: List[Path] = []
        img_stems = {img.stem: img for img in images}
        for stem in sorted(img_stems):
            label_candidate = split_dir / f"{stem}.txt"
            if label_candidate.is_file():
                label_paths.append(label_candidate)
        labels_tuple = tuple(label_paths)

        annotated_count, total_instances = _count_annotated_and_instances(labels_tuple)

        images_per_split[split_name] = images_tuple
        labels_per_split[split_name] = labels_tuple
        stats_per_split[split_name] = SplitStats(
            image_count=len(images),
            annotated_count=annotated_count,
            total_instances=total_instances,
        )

    return DatasetSnapshot(
        yaml_path=yaml_path,
        yaml_data=yaml_data,
        yaml_load_error=yaml_load_error,
        data_root=data_root,
        nc=nc,
        class_names=class_names,
        task_type=task_type,
        images_per_split=images_per_split,
        labels_per_split=labels_per_split,
        stats_per_split=stats_per_split,
        scan_warnings=tuple(warnings),
    )
