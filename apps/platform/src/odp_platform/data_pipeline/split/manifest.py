#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据集清单 (Manifest)
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

@dataclass
class Pair:
    """图片-标签对"""
    image: Path
    label: Path

@dataclass
class DatasetManifest:
    """数据集清单，包含所有有效的图片-标签对及类别列表"""
    pairs: List[Pair] = field(default_factory=list)
    classes: List[str] = field(default_factory=list)
    
    @classmethod
    def from_directories(
        cls,
        images_dir: Path,
        labels_dir: Path,
        classes: List[str],
    ) -> 'DatasetManifest':
        """
        从图片目录和标签目录扫描所有匹配的图片-标签对。
        只保留同时存在图片和对应 .txt 标签文件的项。
        """
        images_dir = Path(images_dir).resolve()
        labels_dir = Path(labels_dir).resolve()
        
        image_exts = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
        
        # 收集所有图片文件（非递归）
        images = {}
        for path in images_dir.iterdir():
            if path.is_file() and path.suffix.lower() in image_exts:
                stem = path.stem
                if stem in images:
                    raise ValueError(f"Duplicate image stem '{stem}' in {images_dir}")
                images[stem] = path
        
        pairs = []
        for stem, img_path in images.items():
            label_path = labels_dir / f"{stem}.txt"
            if label_path.is_file():
                pairs.append(Pair(image=img_path, label=label_path))
        
        # 按图片名称排序，保证可复现
        pairs.sort(key=lambda p: p.image.name)
        
        return cls(pairs=pairs, classes=list(classes))