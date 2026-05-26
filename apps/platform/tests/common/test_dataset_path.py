"""resolve_dataset_path 单元测试."""
from __future__ import annotations

from pathlib import Path

from odp_platform.common.dataset_path import resolve_dataset_path


def test_absolute_path_returned_as_is(tmp_path):
    """绝对路径直接用."""
    yaml = tmp_path / "rsod.yaml"
    yaml.write_text("path: ...")
    assert resolve_dataset_path(yaml) == yaml


def test_filename_falls_back_to_dataset_configs_dir(tmp_path, monkeypatch):
    """仅文件名 → 查 CONFIG_DATASETS_DIR."""
    fake_dir = tmp_path / "datasets"
    fake_dir.mkdir()
    (fake_dir / "rsod.yaml").write_text("path: ...")
    monkeypatch.setattr(
        "odp_platform.common.dataset_path.CONFIG_DATASETS_DIR", fake_dir
    )
    assert resolve_dataset_path("rsod.yaml") == fake_dir / "rsod.yaml"


def test_not_found_returns_original_with_warning(caplog):
    """找不到返回原值 + warning, 不 raise."""
    result = resolve_dataset_path("nonexistent.yaml")
    assert str(result) == "nonexistent.yaml"
    assert "未在 CONFIG_DATASETS_DIR 找到" in caplog.text


def test_filename_with_path_separator(tmp_path, monkeypatch):
    """仅文件名含路径分隔符, 只取 name 部分."""
    fake_dir = tmp_path / "ds"
    fake_dir.mkdir()
    (fake_dir / "cfg.yaml").write_text("a: b")
    monkeypatch.setattr(
        "odp_platform.common.dataset_path.CONFIG_DATASETS_DIR", fake_dir
    )
    result = resolve_dataset_path("sub/cfg.yaml")
    assert result == fake_dir / "cfg.yaml"


def test_relative_path_not_absolute_not_in_config(tmp_path):
    """相对路径且不在 CONFIG_DATASETS_DIR — 返回原值."""
    result = resolve_dataset_path("some/relative/path.yaml")
    assert str(result) == "some/relative/path.yaml"
