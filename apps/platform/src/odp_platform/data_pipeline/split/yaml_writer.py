# apps/platform/src/odp_platform/data_pipeline/split/yaml_writer.py
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
import yaml

class YamlWriter:
    def __init__(self, classes: List[str]) -> None:
        self.classes = classes

    def write(
        self,
        output_path: Path,
        path_rel: Optional[str],          # yaml 中的 path 字段（相对于 yaml 目录的数据集根）
        train_rel: str,
        val_rel: str,
        test_rel: str,
        nc: int,
        random_state: int,
        split_counts: Dict[str, int],
    ) -> None:
        data = {
            "path": path_rel,
            "train": train_rel,
            "val": val_rel,
            "test": test_rel,
            "nc": nc,
            "names": {i: name for i, name in enumerate(self.classes)},
            "odp_meta": {
                "schema_version": 1,
                "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "random_state": random_state,
                "split": {"counts": split_counts},
            },
        }
        # 如果是 None 则移除 path 字段（ultralytics 允许无 path 字段，此时 train/val/test 直接相对于 yaml 目录）
        if path_rel is None:
            del data["path"]

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)