#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
YOLO 数据集转换器（接口等价）

将已有的 YOLO 格式数据集复制到标准输出目录，并返回类别列表。
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Set

from ..registry import register_converter, ConvertOptions

logger = logging.getLogger(__name__)


@register_converter("yolo", ("detect",))
class YoloConverter:
    """
    YOLO 格式数据集转换器。

    输入目录中应包含图片文件（常见扩展名）和对应的 YOLO 标注文件 (.txt)。
    转换器将找出所有有效的图片-标签对，复制到指定的输出目录，
    并返回最终采用的类别名称列表。

    约定：
    - 图片与标签基于文件名（不含扩展名）匹配；
    - 标签文件内容每行：class_id x_center y_center width height（归一化）；
    - 如果 `options.classes` 不为 None，其列表顺序对应 class id（0 → 列表第一项），
      转换时会根据该列表过滤标注（不在范围内的被丢弃）；
    - 如果 `options.classes` 为 None，则自动从标注中收集所有出现的 class id，
      按 id 数值排序后，以十进制数字字符串作为类别名称（如 "0", "1" ...）。
    """

    IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}

    def __init__(
        self,
        input_dir: Path,
        output_images_dir: Path,
        output_labels_dir: Path,
        options: ConvertOptions,
    ) -> None:
        self.input_dir = input_dir.resolve()
        self.output_images_dir = output_images_dir.resolve()
        self.output_labels_dir = output_labels_dir.resolve()
        self.options = options

        if not self.input_dir.is_dir():
            raise NotADirectoryError(f"Input directory does not exist: {self.input_dir}")

        self.output_images_dir.mkdir(parents=True, exist_ok=True)
        self.output_labels_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    def convert(self) -> List[str]:
        # 1. 扫描所有图片（递归，大小写不敏感）
        image_map: Dict[str, Path] = {}  # stem -> image_path
        for path in self.input_dir.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() not in self.IMAGE_EXTENSIONS:
                continue
            stem = path.stem
            if stem in image_map:
                raise ValueError(
                    f"Duplicate image stem '{stem}' found: "
                    f"{image_map[stem]} and {path}"
                )
            image_map[stem] = path

        if not image_map:
            raise FileNotFoundError(f"No image files found in {self.input_dir}")

        # 2. 扫描所有标签文件（.txt）
        label_map: Dict[str, Path] = {}
        for path in self.input_dir.rglob("*.txt"):
            if not path.is_file():
                continue
            stem = path.stem
            if stem in image_map:  # 只关心有对应图片的标签
                if stem in label_map:
                    raise ValueError(
                        f"Duplicate label stem '{stem}' found: "
                        f"{label_map[stem]} and {path}"
                    )
                label_map[stem] = path

        common_stems = sorted(set(image_map.keys()) & set(label_map.keys()))
        if not common_stems:
            raise ValueError("No matching image-label pairs found.")

        # 3. 确定类别映射
        user_classes = self.options.classes
        if user_classes is not None:
            # 用户明确提供类别列表，索引即 class id
            classes = list(user_classes)
            valid_ids = set(range(len(classes)))
        else:
            # 自动收集所有标签中出现的 class id
            collected_ids: Set[int] = set()
            for stem in common_stems:
                label_path = label_map[stem]
                with open(label_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        parts = line.split()
                        if len(parts) < 1:
                            continue
                        try:
                            cls_id = int(float(parts[0]))  # 允许 "0.0" 这类写法
                            collected_ids.add(cls_id)
                        except ValueError:
                            logger.warning(
                                "Invalid class id '%s' in line of %s, skip",
                                parts[0], label_path.name,
                            )
            if not collected_ids:
                raise ValueError("No valid class ids found in labels.")
            sorted_ids = sorted(collected_ids)
            # 类别名称直接使用数字的字符串形式
            classes = [str(i) for i in sorted_ids]
            valid_ids = set(sorted_ids)

        # 4. 复制文件并过滤标注（若需要）
        copied = 0
        for stem in common_stems:
            img_src = image_map[stem]
            lbl_src = label_map[stem]
            img_dst = self.output_images_dir / img_src.name
            lbl_dst = self.output_labels_dir / f"{stem}.txt"

            shutil.copy2(img_src, img_dst)

            if user_classes is not None:
                # 过滤标注行
                new_lines: List[str] = []
                with open(lbl_src, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        parts = line.split()
                        if len(parts) < 5:
                            logger.debug("Malformed line in %s: '%s'", lbl_src.name, line)
                            continue
                        try:
                            cls_id = int(float(parts[0]))
                        except ValueError:
                            continue
                        if cls_id not in valid_ids:
                            continue
                        # 重新组织行：class_id + 4 个坐标（保留原数值不改变）
                        new_line = f"{cls_id} " + " ".join(parts[1:5])
                        new_lines.append(new_line)
                # 写入过滤后的标签（可能为空文件，代表该图片无目标）
                with open(lbl_dst, "w", encoding="utf-8") as f:
                    f.write("\n".join(new_lines) + "\n" if new_lines else "")
            else:
                # 无需过滤，直接复制标签文件（更高效）
                shutil.copy2(lbl_src, lbl_dst)

            copied += 1

        logger.info("YOLO conversion done: %d image-label pairs copied.", copied)
        return classes