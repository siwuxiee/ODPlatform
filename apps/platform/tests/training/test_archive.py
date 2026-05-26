"""archive_checkpoints 单元测试."""
from __future__ import annotations

from pathlib import Path

from odp_platform.training.archive import archive_checkpoints


def test_archive_copies_both(fake_train_dir, tmp_path):
    """正常复制 best.pt 和 last.pt."""
    ckpt_dir = tmp_path / "ckpt"
    result = archive_checkpoints(
        fake_train_dir, "yolo11n.pt", checkpoint_dir=ckpt_dir
    )
    assert "best" in result and "last" in result
    assert result["best"].exists()
    assert result["last"].exists()
    assert "train3" in result["best"].name
    assert "yolo11n" in result["best"].name
    assert "best" in result["best"].name


def test_archive_missing_train_dir_returns_empty(tmp_path):
    """train_dir 不存在 — 返回 {}, warning, 不抛."""
    result = archive_checkpoints(
        tmp_path / "nonexistent", "yolo11n.pt", checkpoint_dir=tmp_path / "ckpt"
    )
    assert result == {}


def test_archive_no_best_no_last(tmp_path):
    """train_dir 存在但 weights/ 是空的 — 跳过, 不抛."""
    empty_train = tmp_path / "train1" / "weights"
    empty_train.mkdir(parents=True)
    result = archive_checkpoints(
        tmp_path / "train1", "yolo11n.pt", checkpoint_dir=tmp_path / "ckpt"
    )
    assert result == {}


def test_archive_only_best(fake_train_dir, tmp_path):
    """只有 best.pt, last.pt 不存在 — 只归档 best."""
    (fake_train_dir / "weights" / "last.pt").unlink()
    ckpt_dir = tmp_path / "ckpt"
    result = archive_checkpoints(
        fake_train_dir, "yolo11n.pt", checkpoint_dir=ckpt_dir
    )
    assert "best" in result
    assert "last" not in result


def test_archive_only_last(fake_train_dir, tmp_path):
    """只有 last.pt, best.pt 不存在 — 只归档 last."""
    (fake_train_dir / "weights" / "best.pt").unlink()
    ckpt_dir = tmp_path / "ckpt"
    result = archive_checkpoints(
        fake_train_dir, "yolo11n.pt", checkpoint_dir=ckpt_dir
    )
    assert "last" in result
    assert "best" not in result
