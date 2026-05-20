# apps/platform/src/odp_platform/data_pipeline/orchestrator.py
"""数据流水线编排器 (Orchestrator)"""

import logging
from pathlib import Path
from typing import List, Optional

from .service import convert_dataset, ConvertOptions
from .split.manifest import DatasetManifest
from .split.splitter import split_pairs
from .split.materializer import DatasetMaterializer
from .split.yaml_writer import YamlWriter

logger = logging.getLogger(__name__)

class Orchestrator:
    MIN_COVERAGE = 0.5

    def __init__(
        self,
        dataset_name: str,
        format_name: str,
        raw_data_dir: Path,              # 原始数据集根目录（含 Annotations/JPEGImages 等）
        output_images_dir: Path,         # 转换后标准化图片暂存目录
        output_labels_dir: Path,         # 转换后标准化标签暂存目录
        config_yaml_path: Path,          # 最终输出的 data.yaml 路径
        output_data_dir: Path,           # 划分后数据集落盘的根目录（如 data/datasets/<name>）
        train_ratio: float = 0.7,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
        random_state: int = 42,
        user_classes: Optional[List[str]] = None,
        task: str = "detect",
    ):
        self.dataset_name = dataset_name
        self.format_name = format_name
        self.raw_data_dir = raw_data_dir
        self.output_images_dir = output_images_dir
        self.output_labels_dir = output_labels_dir
        self.config_yaml_path = config_yaml_path
        self.output_data_dir = output_data_dir
        self.train_ratio = train_ratio
        self.val_ratio = val_ratio
        self.test_ratio = test_ratio
        self.random_state = random_state
        self.user_classes = user_classes
        self.task = task

    def run(self) -> None:
        logger.info("=== 开始处理数据集 '%s' (format=%s) ===", self.dataset_name, self.format_name)

        # 1. 原始覆盖率检查
        self._check_raw_coverage()

        # 2. 格式转换
        logger.info("格式转换...")
        options = ConvertOptions(classes=self.user_classes, task=self.task)
        classes = convert_dataset(
            format_name=self.format_name,
            input_dir=self.raw_data_dir,
            output_images_dir=self.output_images_dir,
            output_labels_dir=self.output_labels_dir,
            options=options,
        )
        logger.info("转换完成，最终类别：%s", classes)

        # 3. 构建清单
        manifest = DatasetManifest.from_directories(
            images_dir=self.output_images_dir,
            labels_dir=self.output_labels_dir,
            classes=classes,
        )
        if not manifest.pairs:
            raise ValueError("转换后没有有效的图片-标签对。")

        # 4. 划分
        train_pairs, val_pairs, test_pairs = split_pairs(
            manifest,
            train_ratio=self.train_ratio,
            val_ratio=self.val_ratio,
            test_ratio=self.test_ratio,
            random_state=self.random_state,
        )

        # 5. 材料化
        materializer = DatasetMaterializer(
            train_images=self.output_data_dir / "images" / "train",
            train_labels=self.output_data_dir / "labels" / "train",
            val_images=self.output_data_dir / "images" / "val",
            val_labels=self.output_data_dir / "labels" / "val",
            test_images=self.output_data_dir / "images" / "test",
            test_labels=self.output_data_dir / "labels" / "test",
        )
        materializer.materialize(train_pairs, val_pairs, test_pairs)

        # 6. 生成 data.yaml（相对路径，适配 ultralytics 规则）
        # 计算相对于 yaml 目录的路径
        yaml_dir = self.config_yaml_path.parent   # 通常是 configs/datasets/
        # 数据集根相对于 yaml 目录的路径：../../data/datasets/<name>
        # 如果 output_data_dir 是绝对路径，可以动态计算，但项目结构固定，这里直接硬编码相对路径
        # 因为 output_data_dir 是 data/datasets/<name>，相对于 configs/datasets/ 就是 ../../data/datasets/<name>
        # 这里我们简单提取 dataset_name 来构造，避免依赖外部 paths
        rel_root = f"../../data/datasets/{self.dataset_name}"

        yaml_writer = YamlWriter(classes=classes)
        yaml_writer.write(
            output_path=self.config_yaml_path,
            path_rel=rel_root,
            train_rel="images/train",
            val_rel="images/val",
            test_rel="images/test",
            nc=len(classes),
            random_state=self.random_state,
            split_counts={
                "train": len(train_pairs),
                "val": len(val_pairs),
                "test": len(test_pairs),
            },
        )

        logger.info("数据集 '%s' 处理完成，配置文件已生成：%s", self.dataset_name, self.config_yaml_path)

    # ------------------------------------------------------------------
    def _check_raw_coverage(self) -> None:
        """检查原始数据集标注覆盖率（fail-fast）"""
        if self.format_name == "pascal_voc":
            ann_dir = self.raw_data_dir / "Annotations"
            img_dir = self.raw_data_dir / "JPEGImages"
            if not ann_dir.is_dir() or not img_dir.is_dir():
                raise FileNotFoundError(f"Annotations/ or JPEGImages/ missing in {self.raw_data_dir}")

            xml_count = len(list(ann_dir.glob("*.xml")))
            img_exts = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
            img_count = sum(1 for f in img_dir.iterdir() if f.suffix.lower() in img_exts)

            if img_count == 0:
                raise ValueError("No images found in JPEGImages/")

            coverage = xml_count / img_count
            logger.info("原始覆盖率：%.2f%% (%d/%d)", coverage * 100, xml_count, img_count)

            if coverage < self.MIN_COVERAGE:
                raise ValueError(
                    f"数据集覆盖率 {coverage:.2%} 低于最小阈值 {self.MIN_COVERAGE:.0%}，"
                    "处理终止。请检查标注完整性。"
                )
        else:
            logger.warning("未实现 format '%s' 的覆盖率检查，跳过", self.format_name)