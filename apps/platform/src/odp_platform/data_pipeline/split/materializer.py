# apps/platform/src/odp_platform/data_pipeline/split/materializer.py
from pathlib import Path
import shutil
from typing import List
from .manifest import Pair

class DatasetMaterializer:
    def __init__(
        self,
        train_images: Path,
        train_labels: Path,
        val_images: Path,
        val_labels: Path,
        test_images: Path,
        test_labels: Path,
    ) -> None:
        self.train_images = train_images
        self.train_labels = train_labels
        self.val_images = val_images
        self.val_labels = val_labels
        self.test_images = test_images
        self.test_labels = test_labels

        for d in [train_images, train_labels, val_images, val_labels, test_images, test_labels]:
            d.mkdir(parents=True, exist_ok=True)

    def materialize(self, train_pairs: List[Pair], val_pairs: List[Pair], test_pairs: List[Pair]) -> None:
        self._copy_set(train_pairs, self.train_images, self.train_labels)
        self._copy_set(val_pairs, self.val_images, self.val_labels)
        self._copy_set(test_pairs, self.test_images, self.test_labels)

    @staticmethod
    def _copy_set(pairs: List[Pair], img_dir: Path, lbl_dir: Path) -> None:
        for pair in pairs:
            shutil.copy2(pair.image, img_dir / pair.image.name)
            shutil.copy2(pair.label, lbl_dir / pair.label.name)