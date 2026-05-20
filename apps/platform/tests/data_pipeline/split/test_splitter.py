from pathlib import Path
import pytest
from odp_platform.data_pipeline.split.manifest import DatasetManifest, Pair
from odp_platform.data_pipeline.split.splitter import split_pairs, RATE_EPSILON

def make_pair(name="img1"):
    return Pair(image=Path(f"images/{name}.jpg"), label=Path(f"labels/{name}.txt"))

def make_manifest(pairs_count=10):
    pairs = [make_pair(f"img{i:02d}") for i in range(pairs_count)]
    return DatasetManifest(pairs=pairs, classes=["class1", "class2"])

class TestSplitPairs:
    def test_basic_split(self):
        manifest = make_manifest(10)
        train, val, test = split_pairs(manifest, 0.7, 0.15, 0.15, random_state=42)
        assert len(train) + len(val) + len(test) == 10
        assert len(train) == 7  # 10*0.7 ≈ 7
        assert len(val) >= 1
        assert len(test) >= 1

    def test_deterministic(self):
        manifest = make_manifest(20)
        train1, val1, test1 = split_pairs(manifest, 0.6, 0.2, 0.2, random_state=123)
        train2, val2, test2 = split_pairs(manifest, 0.6, 0.2, 0.2, random_state=123)
        assert train1 == train2
        assert val1 == val2
        assert test1 == test2

    def test_invalid_ratios_sum(self):
        manifest = make_manifest(10)
        with pytest.raises(ValueError, match=r"Ratios sum to"):
            split_pairs(manifest, 0.5, 0.5, 0.5)  # sum=1.5

    def test_negative_ratio(self):
        manifest = make_manifest(10)
        # 错误信息包含 "train_ratio must be in [0,1]" 片段，正则需转义方括号
        with pytest.raises(ValueError, match=r"train_ratio must be in \[0,1\]"):
            split_pairs(manifest, -0.1, 0.5, 0.6)

    def test_zero_ratio_allowed(self):
        manifest = make_manifest(10)
        train, val, test = split_pairs(manifest, 1.0, 0.0, 0.0, random_state=42)
        assert len(train) == 10
        assert len(val) == 0
        assert len(test) == 0

    def test_empty_manifest_raises(self):
        manifest = DatasetManifest(pairs=[], classes=[])
        with pytest.raises(ValueError, match=r"Cannot split empty"):
            split_pairs(manifest)

    def test_too_few_pairs_raises(self):
        manifest = make_manifest(2)
        with pytest.raises(ValueError, match=r"Need at least"):
            split_pairs(manifest, 0.7, 0.15, 0.15)

    def test_all_pairs_preserved(self):
        manifest = make_manifest(15)
        train, val, test = split_pairs(manifest, 0.7, 0.15, 0.15)
        # 确保所有样本都在集合中（无丢失、无重复）
        combined = list(train) + list(val) + list(test)
        assert len(combined) == 15
        # 用对象的 id 检查去重
        ids = [id(p) for p in combined]
        assert len(set(ids)) == 15