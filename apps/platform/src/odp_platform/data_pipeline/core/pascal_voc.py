#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PASCAL VOC 数据集转换器
"""

from __future__ import annotations

import logging
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Optional, Set

from PIL import Image

from ..registry import register_converter, ConvertOptions

logger = logging.getLogger(__name__)


@register_converter("pascal_voc", ("detect",))
class PascalVOCConverter:
    """将 PASCAL VOC 格式转换为 YOLO 格式。"""

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

        self.annotations_dir = self.input_dir / "Annotations"
        self.images_dir = self.input_dir / "JPEGImages"

        if not self.annotations_dir.is_dir():
            raise FileNotFoundError(f"Annotations directory not found: {self.annotations_dir}")
        if not self.images_dir.is_dir():
            raise FileNotFoundError(f"JPEGImages directory not found: {self.images_dir}")

        self.output_images_dir.mkdir(parents=True, exist_ok=True)
        self.output_labels_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    def convert(self) -> List[str]:
        xml_files = sorted(self.annotations_dir.glob("*.xml"))
        if not xml_files:
            raise ValueError(f"No XML files found in {self.annotations_dir}")

        classes, class_to_id = self._build_class_mapping(xml_files)

        for xml_path in xml_files:
            self._process_one(xml_path, class_to_id)

        return classes

    # ------------------------------------------------------------------
    def _build_class_mapping(self, xml_files: List[Path]):
        user_classes = self.options.classes

        if user_classes is not None:
            classes = list(user_classes)
            class_to_id = {name: idx for idx, name in enumerate(classes)}
        else:
            all_names: Set[str] = set()
            for xml_path in xml_files:
                tree = ET.parse(xml_path)
                root = tree.getroot()
                for obj in root.findall("object"):
                    name = obj.find("name").text
                    if name:
                        all_names.add(name)
            classes = sorted(all_names)
            class_to_id = {name: idx for idx, name in enumerate(classes)}
            logger.info("Auto-detected %d classes: %s", len(classes), classes)

        return classes, class_to_id

    # ------------------------------------------------------------------
    def _process_one(self, xml_path: Path, class_to_id: dict) -> None:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        filename_elem = root.find("filename")
        if filename_elem is None or not filename_elem.text:
            logger.warning("Missing <filename> in %s, skip", xml_path)
            return
        image_filename = filename_elem.text.strip()

        width, height = self._get_image_dimension(root, image_filename)

        src_image_path = self._find_image(image_filename)
        if src_image_path is None:
            logger.warning("Image not found for %s, skip", image_filename)
            return
        dst_image_path = self.output_images_dir / image_filename
        if not dst_image_path.exists():
            shutil.copy2(src_image_path, dst_image_path)

        label_lines: List[str] = []
        for obj in root.findall("object"):
            name_elem = obj.find("name")
            if name_elem is None or not name_elem.text:
                continue
            cls_name = name_elem.text.strip()
            if cls_name not in class_to_id:
                if self.options.classes is not None:
                    continue
                logger.debug("Unknown class '%s' in %s", cls_name, xml_path)
                continue

            cls_id = class_to_id[cls_name]
            bbox = obj.find("bndbox")
            if bbox is None:
                continue
            try:
                xmin = float(bbox.find("xmin").text)
                ymin = float(bbox.find("ymin").text)
                xmax = float(bbox.find("xmax").text)
                ymax = float(bbox.find("ymax").text)
            except (AttributeError, ValueError) as exc:
                logger.warning("Invalid bndbox in %s: %s", xml_path, exc)
                continue

            x_center = (xmin + xmax) / 2.0 / width
            y_center = (ymin + ymax) / 2.0 / height
            w = (xmax - xmin) / width
            h = (ymax - ymin) / height

            x_center = max(0.0, min(1.0, x_center))
            y_center = max(0.0, min(1.0, y_center))
            w = max(0.0, min(1.0, w))
            h = max(0.0, min(1.0, h))

            label_lines.append(f"{cls_id} {x_center:.6f} {y_center:.6f} {w:.6f} {h:.6f}")

        label_filename = Path(image_filename).stem + ".txt"
        label_path = self.output_labels_dir / label_filename
        with open(label_path, "w", encoding="utf-8") as f:
            f.write("\n".join(label_lines))

    # ------------------------------------------------------------------
    def _get_image_dimension(self, root: ET.Element, image_filename: str):
        size_elem = root.find("size")
        if size_elem is not None:
            width_elem = size_elem.find("width")
            height_elem = size_elem.find("height")
            if width_elem is not None and height_elem is not None:
                try:
                    return int(width_elem.text), int(height_elem.text)
                except (ValueError, TypeError):
                    pass

        # fallback: read from image file
        img_path = self._find_image(image_filename)
        if img_path is None:
            raise FileNotFoundError(f"Cannot determine size: image {image_filename} not found")
        with Image.open(img_path) as im:
            return im.size

    def _find_image(self, image_filename: str) -> Optional[Path]:
        direct = self.images_dir / image_filename
        if direct.exists():
            return direct
        stem = Path(image_filename).stem.lower()
        exts = (".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff")
        for ext in exts:
            for variant in (f"{stem}{ext}", f"{stem}{ext.upper()}"):
                cand = self.images_dir / variant
                if cand.exists():
                    return cand
        return None