#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
COCO 数据集转换器
"""

from __future__ import annotations

import json
import logging
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from PIL import Image

from ..registry import register_converter, ConvertOptions

logger = logging.getLogger(__name__)


@register_converter("coco", ("detect", "segment"))
class CocoConverter:
    """
    将 COCO JSON 转换为 YOLO 格式（检测或分割）。
    转换过程使用临时目录，完成后原子性地替换输出目录。
    """

    def __init__(
        self,
        input_dir: Path,
        output_images_dir: Path,
        output_labels_dir: Path,
        options: ConvertOptions,
    ) -> None:
        self.input_dir = input_dir
        self.output_images_dir = output_images_dir
        self.output_labels_dir = output_labels_dir
        self.options = options

        # 定位 JSON
        self.json_path = self._find_json()
        if self.json_path is None:
            raise FileNotFoundError(f"No JSON annotation file found in {input_dir}")

        # 图片根目录（推测）
        self.images_root = self._guess_images_root()

    # ------------------------------------------------------------------
    def convert(self) -> List[str]:
        with open(self.json_path, "r", encoding="utf-8") as f:
            coco = json.load(f)

        images_index = self._build_image_index(coco.get("images", []))
        cat_id_to_name = self._build_category_index(coco.get("categories", []))
        classes, class_to_id = self._resolve_classes(cat_id_to_name)

        # 中转目录
        tmp_base = Path(tempfile.mkdtemp())
        try:
            tmp_images = tmp_base / "images"
            tmp_labels = tmp_base / "labels"
            tmp_images.mkdir(parents=True)
            tmp_labels.mkdir(parents=True)

            # 已复制的图片缓存（避免重复判断）
            copied_images: Set[str] = set()
            total, skipped = 0, 0
            for ann in coco.get("annotations", []):
                image_id = ann.get("image_id")
                img_info = images_index.get(image_id)
                if img_info is None:
                    logger.warning("Unknown image_id %s, skip", image_id)
                    continue

                file_name = img_info["file_name"]
                # 复制图片（每个文件只复制一次）
                if file_name not in copied_images:
                    src = self._resolve_image(file_name)
                    if src is None:
                        logger.warning("Image '%s' not found, skip", file_name)
                        skipped += 1
                        continue
                    shutil.copy2(src, tmp_images / file_name)
                    copied_images.add(file_name)

                # 生成标签行
                label_line = self._annotation_to_yolo(
                    ann,
                    img_info,
                    cat_id_to_name,
                    class_to_id,
                    self.options.task,
                )
                if label_line is None:
                    skipped += 1
                    continue

                label_path = tmp_labels / f"{Path(file_name).stem}.txt"
                with open(label_path, "a", encoding="utf-8") as f:
                    f.write(label_line + "\n")
                total += 1

            logger.info("Converted %d annotations, skipped %d", total, skipped)

            # 原子搬移
            if self.output_images_dir.exists():
                shutil.rmtree(self.output_images_dir)
            if self.output_labels_dir.exists():
                shutil.rmtree(self.output_labels_dir)
            self.output_images_dir.parent.mkdir(parents=True, exist_ok=True)
            self.output_labels_dir.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(tmp_images), str(self.output_images_dir))
            shutil.move(str(tmp_labels), str(self.output_labels_dir))

            return classes

        finally:
            shutil.rmtree(tmp_base, ignore_errors=True)

    # ------------------------------------------------------------------
    # 按需重开一条辅助方法
    def _annotation_to_yolo(
        self,
        ann: dict,
        img_info: dict,
        cat_id_to_name: Dict[int, str],
        class_to_id: Dict[str, int],
        task: str,
    ) -> Optional[str]:
        """单条标注 → 一行 YOLO 文本。"""
        cat_id = ann.get("category_id")
        if cat_id is None:
            logger.warning("Missing category_id")
            return None
        cat_name = cat_id_to_name.get(cat_id)
        if cat_name is None:
            logger.warning("Unknown category_id %d", cat_id)
            return None
        if cat_name not in class_to_id:
            # 用户过滤掉了该类，忽略
            return None

        cls_id = class_to_id[cat_name]

        # 获取图片宽高
        width = img_info.get("width")
        height = img_info.get("height")
        if width is None or height is None:
            # 回退从实际图片读取
            src = self._resolve_image(img_info["file_name"])
            if src is None:
                logger.warning("Cannot determine image size for %s", img_info["file_name"])
                return None
            with Image.open(src) as im:
                width, height = im.size

        if task == "segment":
            # 处理分割
            seg = ann.get("segmentation")
            if not seg:
                # 有些数据集只有 bbox，没有 segmentation，此时若要求 segment 则跳过
                logger.debug("No segmentation for image_id %s, skipping segment conversion", ann.get("image_id"))
                return None
            # COCO segmentation 可能是 list of lists (polygons) 或 RLE (counts)
            if isinstance(seg, list):
                # 取第一个多边形（简化为单多边形）
                if len(seg) == 0:
                    return None
                points = seg[0]  # list of floats: [x1, y1, x2, y2, ...]
                # 归一化
                norm_points = []
                for i in range(0, len(points), 2):
                    x = max(0.0, min(1.0, points[i] / width))
                    y = max(0.0, min(1.0, points[i + 1] / height))
                    norm_points.extend([x, y])
                # 构建标签行：cls_id 后跟归一化坐标对
                line = f"{cls_id} " + " ".join(f"{v:.6f}" for v in norm_points)
                return line
            else:
                # RLE 格式暂不支持，跳过
                logger.debug("Non-polygon segmentation (RLE) not supported for image_id %s", ann.get("image_id"))
                return None
        else:
            # 检测模式
            bbox = ann.get("bbox")
            if not bbox or len(bbox) != 4:
                return None
            x, y, w, h = bbox
            if w <= 0 or h <= 0:
                return None
            x_center = (x + w / 2) / width
            y_center = (y + h / 2) / height
            norm_w = w / width
            norm_h = h / height
            # 裁剪
            x_center = max(0.0, min(1.0, x_center))
            y_center = max(0.0, min(1.0, y_center))
            norm_w = max(0.0, min(1.0, norm_w))
            norm_h = max(0.0, min(1.0, norm_h))
            return f"{cls_id} {x_center:.6f} {y_center:.6f} {norm_w:.6f} {norm_h:.6f}"

    # ------------------------------------------------------------------
    def _find_json(self) -> Optional[Path]:
        json_files = list(self.input_dir.glob("*.json"))
        if not json_files:
            return None
        if len(json_files) > 1:
            raise ValueError(
                f"Multiple JSON files found in {self.input_dir}: "
                f"{[f.name for f in json_files]}. Please keep only one."
            )
        return json_files[0]

    def _guess_images_root(self) -> Path:
        candidates = [
            self.input_dir / "images",
            self.input_dir / "Images",
            self.input_dir / "images",
            self.input_dir,
        ]
        for cand in candidates:
            if cand.is_dir():
                return cand
        return self.input_dir

    @staticmethod
    def _build_image_index(images: list) -> Dict[int, dict]:
        index = {}
        for img in images:
            if "id" in img and "file_name" in img:
                index[img["id"]] = img
        return index

    @staticmethod
    def _build_category_index(categories: list) -> Dict[int, str]:
        index = {}
        for cat in categories:
            if "id" in cat and "name" in cat:
                index[cat["id"]] = cat["name"]
        return index

    def _resolve_classes(self, cat_id_to_name: Dict[int, str]) -> Tuple[List[str], Dict[str, int]]:
        user_classes = self.options.classes
        if user_classes is not None:
            classes = list(user_classes)
            all_names = set(cat_id_to_name.values())
            for cls in user_classes:
                if cls not in all_names:
                    logger.warning("User class '%s' not in dataset categories", cls)
        else:
            classes = sorted(set(cat_id_to_name.values()))
            logger.info("Auto-detected %d classes: %s", len(classes), classes)

        class_to_id = {name: idx for idx, name in enumerate(classes)}
        return classes, class_to_id

    def _resolve_image(self, file_name: str) -> Optional[Path]:
        """在 images_root 中查找图片文件（支持不同扩展名）。"""
        direct = self.images_root / file_name
        if direct.exists():
            return direct
        stem = Path(file_name).stem.lower()
        exts = (".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff")
        for ext in exts:
            for variant in (f"{stem}{ext}", f"{stem}{ext.upper()}"):
                cand = self.images_root / variant
                if cand.exists():
                    return cand
        # 如果还没找到，尝试递归搜索（大型数据集可能慢，但保底）
        for cand in self.images_root.rglob(file_name):
            return cand
        return None