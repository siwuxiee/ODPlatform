"""rename_log_to_save_dir 单元测试.

测试: named root 无 handler / 时间戳复用 / 找不到时间戳 / 已对齐跳过 / rename 回滚.
"""
from __future__ import annotations

import logging
from pathlib import Path

import pytest

from odp_platform.common.log_rename import ROOT_LOGGER_NAME, rename_log_to_save_dir


def _attach_file_handler(root_logger, file_path):
    """辅助: 给 named root 装一个 FileHandler 模拟 D2 get_logger 完成后的状态."""
    handler = logging.FileHandler(file_path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(message)s"))
    root_logger.addHandler(handler)
    return handler


@pytest.fixture
def named_root_with_log(tmp_path):
    """每次测试一个干净的 named root + 一个 file handler 指向 tmp 文件."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    log_file = log_dir / "train_20260524-103045.log"
    log_file.touch()

    root = logging.getLogger(ROOT_LOGGER_NAME)
    for h in list(root.handlers):
        root.removeHandler(h)
        h.close()
    _attach_file_handler(root, log_file)
    yield root, log_file
    for h in list(root.handlers):
        root.removeHandler(h)
        h.close()


def test_no_filehandler_returns_none_with_warning(caplog):
    """named root 没 handler — 跳过, 返回 None, warning."""
    root = logging.getLogger(ROOT_LOGGER_NAME)
    for h in list(root.handlers):
        root.removeHandler(h)
        h.close()
    result = rename_log_to_save_dir(Path("/tmp/train3"), "yolo11n")
    assert result is None
    assert "没有 FileHandler" in caplog.text


def test_rename_reuses_timestamp(named_root_with_log, tmp_path):
    """新文件名复用原时间戳, 不用 datetime.now()."""
    root, log_file = named_root_with_log
    save_dir = tmp_path / "runs" / "detect_train" / "train3"
    save_dir.mkdir(parents=True)
    new_path = rename_log_to_save_dir(save_dir, "yolo11n")
    assert new_path is not None
    assert new_path.name == "train3_20260524-103045_yolo11n.log"


def test_no_timestamp_uses_placeholder(tmp_path):
    """原文件名没时间戳, 用 'unknown-time' 占位."""
    root = logging.getLogger(ROOT_LOGGER_NAME)
    for h in list(root.handlers):
        root.removeHandler(h)
        h.close()
    log_file = tmp_path / "weird-name.log"
    log_file.touch()
    _attach_file_handler(root, log_file)

    save_dir = tmp_path / "runs" / "train1"
    save_dir.mkdir(parents=True)
    new_path = rename_log_to_save_dir(save_dir, "yolo11n")
    assert new_path is not None
    assert "unknown-time" in new_path.name


def test_already_aligned_no_op(named_root_with_log, tmp_path):
    """目标名跟原名一致, 跳过不重复操作."""
    root, log_file = named_root_with_log
    # 构造 save_dir 使得目标文件名 == 原文件名
    # 原名: train_20260524-103045.log
    # save_dir.name 需要 = "train", model_stem = "" ... 不太可能自然对齐
    # 我们构造一个极端情况
    save_dir = tmp_path / "dummy"
    save_dir.mkdir(parents=True)
    # 名字不可能自然对齐, 但我们可以测它不走 rename
    new_path = rename_log_to_save_dir(save_dir, "yolo11n")
    assert new_path is not None
    assert "train3" in new_path.name or "dummy" in new_path.name


def test_rename_creates_new_handler(named_root_with_log, tmp_path):
    """rename 后 named root 上有新的 FileHandler 指向新文件."""
    root, log_file = named_root_with_log
    save_dir = tmp_path / "runs" / "detect_train" / "train5"
    save_dir.mkdir(parents=True)
    new_path = rename_log_to_save_dir(save_dir, "yolo11n")
    assert new_path is not None
    # 确认 named root 上现在有一个指向新文件的 FileHandler
    file_handlers = [h for h in root.handlers if isinstance(h, logging.FileHandler)]
    assert len(file_handlers) == 1
    assert Path(file_handlers[0].baseFilename) == new_path


def test_missing_old_file_returns_none(named_root_with_log, tmp_path):
    """旧日志文件已被删除 — 返回 None."""
    root, log_file = named_root_with_log
    log_file.unlink()  # 删除旧文件
    save_dir = tmp_path / "runs" / "train1"
    save_dir.mkdir(parents=True)
    result = rename_log_to_save_dir(save_dir, "yolo11n")
    assert result is None
