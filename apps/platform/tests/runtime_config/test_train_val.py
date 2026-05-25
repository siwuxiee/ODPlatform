#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""YOLOTrainConfig + YOLOValConfig 行为契约."""
from __future__ import annotations

import warnings
import pytest
from pydantic import ValidationError

from odp_platform.common.constants     import Task
from odp_platform.runtime_config.train import YOLOTrainConfig
from odp_platform.runtime_config.val   import YOLOValConfig


# ============================================================
# task / experiment_name 拆分
# ============================================================

class TestTaskExperimentNameSplit:
    """task = SSoT 语义; experiment_name = 实验标识 — 必须正交."""

    def test_task_defaults_to_detect(self):
        assert YOLOTrainConfig().task == Task.DETECT
        assert YOLOValConfig().task   == Task.DETECT

    @pytest.mark.parametrize("invalid_task", [
        "detect_v2",
        "Detection",
        "DETECT",
        "detect_baseline",
        "",
        "pose",
    ])
    def test_train_task_rejects_invalid(self, invalid_task):
        with pytest.raises(ValidationError) as exc_info:
            YOLOTrainConfig(task=invalid_task)
        msg = str(exc_info.value)
        assert "experiment_name" in msg, \
            f"task 报错应指引用 experiment_name; 实际: {msg}"

    @pytest.mark.parametrize("invalid_task", [
        "detect_v2", "Detection", "segmentation",
    ])
    def test_val_task_rejects_invalid(self, invalid_task):
        with pytest.raises(ValidationError):
            YOLOValConfig(task=invalid_task)

    @pytest.mark.parametrize("name", [
        "baseline", "helmet_v1", "lr001_aug_strong",
        "exp-2024-05", "model_v3.1",
    ])
    def test_experiment_name_accepts_free_string(self, name):
        c = YOLOTrainConfig(experiment_name=name)
        assert c.experiment_name == name

    def test_experiment_name_can_be_none(self):
        c = YOLOTrainConfig()
        assert c.experiment_name is None


# ============================================================
# FRAMEWORK_ONLY_FIELDS 在 train vs val 不同
# ============================================================

class TestFrameworkOnlyFields:
    """train 的 task 传给 ultralytics; val 的 task 不传."""

    def test_train_passes_task_to_ultralytics(self):
        c = YOLOTrainConfig(task="detect", experiment_name="exp1")
        kw = c.to_ultralytics_kwargs()
        assert "task" in kw
        assert kw["task"] == "detect"
        assert "experiment_name" not in kw

    def test_val_does_not_pass_task(self):
        c = YOLOValConfig(task="detect", experiment_name="vexp")
        kw = c.to_ultralytics_kwargs()
        assert "task" not in kw
        assert "experiment_name" not in kw


# ============================================================
# 跨字段验证
# ============================================================

class TestCrossFieldValidation:
    def test_save_false_with_save_period_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            YOLOTrainConfig(save=False, save_period=10)
        assert "save_period" in str(exc_info.value)

    def test_mosaic_zero_with_close_mosaic_warns(self):
        with warnings.catch_warnings(record=True) as ws:
            warnings.simplefilter("always")
            YOLOTrainConfig(mosaic=0.0, close_mosaic=10)
            assert any(
                "close_mosaic 将不会生效" in str(w.message)
                for w in ws
            )

    def test_save_false_and_save_period_minus_one_ok(self):
        c = YOLOTrainConfig(save=False, save_period=-1)
        assert c.save is False and c.save_period == -1


# ============================================================
# val 特有字段
# ============================================================

class TestValSpecific:
    def test_split_default(self):
        assert YOLOValConfig().split == "val"

    @pytest.mark.parametrize("invalid", ["testing", "VAL", "validate", ""])
    def test_split_rejects_invalid(self, invalid):
        with pytest.raises(ValidationError):
            YOLOValConfig(split=invalid)

    @pytest.mark.parametrize("valid", ["train", "val", "test"])
    def test_split_accepts_valid(self, valid):
        c = YOLOValConfig(split=valid)
        assert c.split == valid

    def test_conf_default_low_for_mAP(self):
        assert YOLOValConfig().conf == 0.001


# ============================================================
# extra='forbid' 从 BaseConfig 继承到子类
# ============================================================

def test_train_extra_forbid_inherited():
    with pytest.raises(ValidationError):
        YOLOTrainConfig(epchs=300)


def test_val_extra_forbid_inherited():
    with pytest.raises(ValidationError):
        YOLOValConfig(spilt="val")


# ============================================================
# 完整字段分组
# ============================================================

EXPECTED_TRAIN_GROUPS = {
    "核心参数", "输入配置", "设备配置", "输出配置", "基础设置",
    "训练控制", "优化器配置", "学习率预热", "损失权重",
    "数据增强-颜色", "数据增强-几何", "数据增强-拼接",
    "验证和输出", "任务特定", "高级设置",
}


def test_train_field_groups_complete():
    groups = set(YOLOTrainConfig().get_field_groups().keys())
    missing = EXPECTED_TRAIN_GROUPS - groups
    assert not missing, f"train 缺分组: {missing}"


# ============================================================
# val: segment 专属字段在 detect 任务下应警告
# ============================================================

@pytest.mark.parametrize("mask_ratio,overlap_mask,should_warn", [
    (4, True,  False),
    (2, True,  True),
    (4, False, True),
    (2, False, True),
])
def test_val_segment_only_fields_warn_on_detect(mask_ratio, overlap_mask, should_warn):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        YOLOValConfig(
            task=Task.DETECT,
            mask_ratio=mask_ratio,
            overlap_mask=overlap_mask,
        )

    seg_warnings = [w for w in caught if "segment 任务有效" in str(w.message)]
    if should_warn:
        assert len(seg_warnings) == 1
    else:
        assert not seg_warnings
