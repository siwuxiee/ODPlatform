"""TrainMetrics + log_train_metrics 单元测试."""
from __future__ import annotations

import logging
import math
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest

from odp_platform.common.result import TrainMetrics, _safe_float, log_train_metrics


# ──── _safe_float ──────────────────────────────────────────────

def test_safe_float_none_returns_nan():
    assert math.isnan(_safe_float(None))


def test_safe_float_invalid_string_returns_nan():
    assert math.isnan(_safe_float("not-a-number"))


def test_safe_float_numpy_scalar():
    assert _safe_float(np.float32(3.14)) == pytest.approx(3.14)


# ──── TrainMetrics.from_yolo_results — detect ──────────────────

def test_train_metrics_from_det_results(mock_det_results):
    metrics = TrainMetrics.from_yolo_results(mock_det_results)
    assert metrics.task == "detect"
    assert metrics.overall["fitness"] == pytest.approx(0.5805)
    assert metrics.overall["metrics/mAP50(B)"] == pytest.approx(0.6912)
    assert "person" in metrics.class_map_50_95
    assert metrics.class_map_50_95["person"] == pytest.approx(0.4521)


def test_train_metrics_speed_total_excludes_nan(mock_det_results):
    """speed_ms['total'] = sum(非 nan)."""
    mock_det_results.speed["loss"] = None  # 让 loss 变 nan
    metrics = TrainMetrics.from_yolo_results(mock_det_results)
    expected = 1.234 + 12.345 + 0.567
    assert metrics.speed_ms["total"] == pytest.approx(expected, abs=1e-3)


def test_train_metrics_speed_all_nan_total_is_nan(mock_det_results):
    """全部 speed 都是 None — total = nan."""
    mock_det_results.speed = {}
    metrics = TrainMetrics.from_yolo_results(mock_det_results)
    assert math.isnan(metrics.speed_ms["total"])


def test_train_metrics_no_maps(mock_det_results):
    """maps 为空 — class_map_50_95 为空."""
    mock_det_results.maps = np.array([])
    mock_det_results.names = {}
    metrics = TrainMetrics.from_yolo_results(mock_det_results)
    assert metrics.class_map_50_95 == {}


# ──── TrainMetrics.from_yolo_results — segment ─────────────────

def test_train_metrics_from_segment_results(mock_segment_results):
    metrics = TrainMetrics.from_yolo_results(mock_segment_results)
    assert metrics.task == "segment"
    assert metrics.overall["metrics/mAP50(M)"] == pytest.approx(0.66)
    assert "person" in metrics.class_map_50_95


# ──── TrainMetrics.from_yolo_results — save_dir fallback ───────

def test_train_metrics_save_dir_from_trainer():
    """results 无 save_dir 时 fallback 到 trainer.save_dir."""
    results = MagicMock()
    results.task = "detect"
    results.save_dir = None
    results.fitness = 0.5
    results.speed = {}
    results.results_dict = {}
    results.maps = np.array([])
    results.names = {}
    trainer = MagicMock()
    trainer.save_dir = Path("/tmp/trainer_save")
    metrics = TrainMetrics.from_yolo_results(results, model_trainer=trainer)
    assert metrics.save_dir == Path("/tmp/trainer_save")


# ──── to_dict ──────────────────────────────────────────────────

def test_to_dict_nan_converts_to_none():
    """to_dict 时 NaN → None, 让 JSON 能序列化."""
    metrics = TrainMetrics(
        task="detect", save_dir=Path("/tmp"),
        timestamp="2026-05-24T10:00:00",
        speed_ms={"preprocess": math.nan},
        overall={"fitness": 0.5},
    )
    d = metrics.to_dict()
    assert d["speed_ms"]["preprocess"] is None
    assert d["overall"]["fitness"] == 0.5


def test_to_dict_save_dir_is_str():
    metrics = TrainMetrics(
        task="detect", save_dir=Path("/tmp/runs"),
        timestamp="2026-05-24T10:00:00",
        speed_ms={}, overall={"fitness": 0.5},
    )
    d = metrics.to_dict()
    assert isinstance(d["save_dir"], str)


def test_to_dict_class_map_nan_handling():
    metrics = TrainMetrics(
        task="detect", save_dir=Path("/tmp"),
        timestamp="2026-05-24T10:00:00",
        speed_ms={}, overall={"fitness": 0.5},
        class_map_50_95={"person": math.nan, "car": 0.5},
    )
    d = metrics.to_dict()
    assert d["class_map_50_95"]["person"] is None
    assert d["class_map_50_95"]["car"] == 0.5


# ──── log_train_metrics ────────────────────────────────────────

def test_log_train_metrics_unknown_task_falls_back(caplog):
    """task='unknown' 时打 results_dict 全量, 不崩."""
    caplog.set_level(logging.INFO)
    metrics = TrainMetrics(
        task="unknown", save_dir=Path("/tmp"),
        timestamp="2026-05-24T10:00:00",
        speed_ms={}, overall={"fitness": 0.5, "metric_x": 0.7},
    )
    log_train_metrics(metrics)
    assert "不在 _METRIC_FIELDS_BY_TASK" in caplog.text
    assert "metric_x" in caplog.text


def test_log_train_metrics_detect_logs_4_metrics(mock_det_results, caplog):
    """detect 任务 4 个指标全部 log."""
    caplog.set_level(logging.INFO)
    metrics = TrainMetrics.from_yolo_results(mock_det_results)
    log_train_metrics(metrics)
    for k in ("mAP50(B)", "mAP50-95(B)", "Precision(B)", "Recall(B)"):
        assert k in caplog.text


def test_log_train_metrics_segment_logs_8_metrics(mock_segment_results, caplog):
    """segment 任务 8 个指标全部 log."""
    caplog.set_level(logging.INFO)
    metrics = TrainMetrics.from_yolo_results(mock_segment_results)
    log_train_metrics(metrics)
    for k in ("mAP50(B)", "mAP50(M)", "Precision(M)", "Recall(M)"):
        assert k in caplog.text


def test_log_train_metrics_with_custom_logger(mock_det_results):
    """传入自定义 logger — 使用传入的 logger."""
    custom_logger = MagicMock()
    metrics = TrainMetrics.from_yolo_results(mock_det_results)
    log_train_metrics(metrics, logger=custom_logger)
    assert custom_logger.info.call_count > 0


def test_log_train_metrics_empty_class_map(mock_det_results, caplog):
    """class_map_50_95 为空时跳过类别 mAP 段."""
    caplog.set_level(logging.INFO)
    mock_det_results.maps = np.array([])
    mock_det_results.names = {}
    metrics = TrainMetrics.from_yolo_results(mock_det_results)
    log_train_metrics(metrics)
    assert "类别级 mAP" not in caplog.text


def test_log_train_metrics_all_nan_class_map(mock_det_results, caplog):
    """class_map_50_95 全部 NaN — 打印 warning."""
    caplog.set_level(logging.INFO)
    mock_det_results.maps = np.array([float("nan"), float("nan")])
    mock_det_results.names = {0: "a", 1: "b"}
    metrics = TrainMetrics.from_yolo_results(mock_det_results)
    log_train_metrics(metrics)
    assert "类别 mAP 全为 NaN" in caplog.text


# ──── misc ─────────────────────────────────────────────────────

def test_train_metrics_speed_missing_key_is_nan(mock_det_results):
    """speed 缺某个 key — 默认 nan."""
    del mock_det_results.speed["loss"]
    metrics = TrainMetrics.from_yolo_results(mock_det_results)
    assert math.isnan(metrics.speed_ms["loss"])


def test_train_metrics_none_speed():
    """speed 为 None."""
    results = MagicMock()
    results.task = "detect"
    results.save_dir = Path("/tmp")
    results.fitness = 0.5
    results.speed = None
    results.results_dict = {}
    results.maps = np.array([])
    results.names = {}
    metrics = TrainMetrics.from_yolo_results(results)
    assert math.isnan(metrics.speed_ms["preprocess"])
