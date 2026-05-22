import json
import tempfile
from pathlib import Path

import pytest
import yaml

from odp_platform.data_validation import (
    CheckSeverity,
    validate_dataset,
)


def _make_minimal_dataset(tmp_path: Path, nc: int = 2) -> Path:
    """创建最小数据集：train/val 各 2 张图 + 标签，stem 跨 split 唯一"""
    data_dir = tmp_path / "data"
    for split_idx, split in enumerate(("train", "val")):
        img_dir = data_dir / split
        img_dir.mkdir(parents=True)
        for i in range(2):
            stem = f"{split}_{i}"
            (img_dir / f"{stem}.jpg").touch()
            (img_dir / f"{stem}.txt").write_text("0 0.5 0.5 0.1 0.1\n", encoding="utf-8")

    yaml_path = tmp_path / "dataset.yaml"
    yaml_path.write_text(
        yaml.dump({
            "path": str(data_dir),
            "train": "train",
            "val": "val",
            "nc": nc,
            "names": ["cat", "dog"],
        }),
        encoding="utf-8",
    )
    return yaml_path


def test_healthy_dataset_all_pass(tmp_path: Path):
    yaml_path = _make_minimal_dataset(tmp_path)
    report = validate_dataset(yaml_path, run_dir=tmp_path / "runs" / "test", write_report=True)

    assert report.overall_severity == CheckSeverity.PASS
    assert report.exit_code == 0
    assert len(report.results) >= 4

    for r in report.results:
        assert r.severity in (CheckSeverity.PASS, CheckSeverity.INFO), \
            f"check '{r.name}' returned {r.severity}: {r.summary}"


def test_report_json_written(tmp_path: Path):
    yaml_path = _make_minimal_dataset(tmp_path)
    run_dir = tmp_path / "runs" / "json_test"
    report = validate_dataset(yaml_path, run_dir=run_dir, write_report=True)

    assert report.report_path is not None
    assert report.report_path.exists()
    data = json.loads(report.report_path.read_text(encoding="utf-8"))
    assert data["run_id"] == report.run_id
    assert data["overall_severity"] == CheckSeverity.PASS
    assert data["exit_code"] == 0


def test_exit_code_with_errors(tmp_path: Path):
    """缺失标签导致 ERROR → exit_code 2"""
    data_dir = tmp_path / "bad_data"
    for split in ("train", "val"):
        img_dir = data_dir / split
        img_dir.mkdir(parents=True)
        for i in range(3):
            (img_dir / f"{i}.jpg").touch()
        # 只给 1 张图配标签 → missing_ratio = 4/6 ≈ 0.67 ≥ 0.5 → ERROR
        (img_dir / "0.txt").write_text("0 0.5 0.5 0.1 0.1\n", encoding="utf-8")

    yaml_path = tmp_path / "bad.yaml"
    yaml_path.write_text(
        yaml.dump({
            "path": str(data_dir),
            "train": "train",
            "val": "val",
            "nc": 2,
            "names": ["cat", "dog"],
        }),
        encoding="utf-8",
    )

    report = validate_dataset(yaml_path, run_dir=tmp_path / "runs" / "bad", write_report=False)
    assert report.exit_code == 2


def test_no_report_flag(tmp_path: Path):
    yaml_path = _make_minimal_dataset(tmp_path)
    run_dir = tmp_path / "runs" / "no_report"
    report = validate_dataset(yaml_path, run_dir=run_dir, write_report=False)

    assert report.report_path is not None
    assert not report.report_path.exists()


def test_counts_by_severity(tmp_path: Path):
    yaml_path = _make_minimal_dataset(tmp_path)
    report = validate_dataset(yaml_path, run_dir=tmp_path / "runs" / "counts", write_report=False)

    counts = report.counts_by_severity
    total = sum(counts.values())
    assert total == len(report.results)
    assert counts[CheckSeverity.ERROR] == 0
    assert counts[CheckSeverity.WARNING] == 0


def test_split_uniqueness_detects_leak(tmp_path: Path):
    yaml_path = _make_minimal_dataset(tmp_path)

    # 把 train 的一张图复制到 val → stem 重复
    data_dir = tmp_path / "data"
    train_img = list((data_dir / "train").glob("*.jpg"))[0]
    import shutil
    shutil.copy(train_img, data_dir / "val" / train_img.name)

    report = validate_dataset(yaml_path, run_dir=tmp_path / "runs" / "leak", write_report=False)

    split_result = next(r for r in report.results if r.name == "split_uniqueness")
    assert split_result.severity == CheckSeverity.ERROR
    assert report.exit_code == 2
