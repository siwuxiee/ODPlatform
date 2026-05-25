#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""ConfigGenerator: YAML 模板生成."""
from __future__ import annotations

from pathlib import Path

import pytest

from odp_platform.runtime_config.generator import ConfigGenerator
from odp_platform.runtime_config.train     import YOLOTrainConfig
from odp_platform.runtime_config.val       import YOLOValConfig
from odp_platform.runtime_config.loaders   import YAMLLoader


class TestFormatValue:
    def setup_method(self):
        self.g = ConfigGenerator()

    def test_none(self):
        assert self.g._format_value(None) == "null"

    @pytest.mark.parametrize("val,expected", [
        (True,  "true"),
        (False, "false"),
    ])
    def test_bool(self, val, expected):
        assert self.g._format_value(val) == expected

    @pytest.mark.parametrize("val,expected", [
        (16,    "16"),
        (-1,    "-1"),
        (0.001, "0.001"),
    ])
    def test_numbers(self, val, expected):
        assert self.g._format_value(val) == expected

    @pytest.mark.parametrize("val,expected", [
        ("yolo.pt", "yolo.pt"),
        ("a:b",    '"a:b"'),
        ("#tag",   '"#tag"'),
        ("[x]",    '"[x]"'),
    ])
    def test_strings(self, val, expected):
        assert self.g._format_value(val) == expected

    def test_lists(self):
        assert self.g._format_value([1, 2, 3]) == "[1, 2, 3]"
        assert self.g._format_value([])        == "[]"
        formatted = self.g._format_value([True, False])
        assert "True" in formatted and "False" in formatted


class TestGenerate:
    def test_basic_generation(self, tmp_path):
        g = ConfigGenerator()
        out = tmp_path / "train.yaml"
        assert g.generate(YOLOTrainConfig, out, overwrite=True) is True
        assert out.exists()

        content = out.read_text(encoding="utf-8")
        assert "自动生成时间" in content
        assert "odp-gen-config" in content
        for group in ["核心参数", "训练控制", "优化器配置", "高级设置"]:
            assert f"# {group}" in content
        for field in ["task", "experiment_name", "epochs", "lr0"]:
            assert f"{field}:" in content
        assert "# 示例: " in content
        assert "# 提示:"  in content
        assert "CLI > YAML > DEFAULT" in content

    def test_generated_yaml_roundtrips(self, tmp_path):
        """生成的 YAML 必须能被 YAMLLoader 完整解析回来."""
        out = tmp_path / "train.yaml"
        ConfigGenerator().generate(YOLOTrainConfig, out, overwrite=True)

        parsed = YAMLLoader().load(out)
        assert parsed["epochs"]    == 100
        assert parsed["batch"]     == 16
        assert parsed["amp"]       is True
        assert parsed["task"]      == "detect"

    def test_default_no_overwrite(self, tmp_path):
        out = tmp_path / "train.yaml"
        g = ConfigGenerator()
        g.generate(YOLOTrainConfig, out, overwrite=True)

        original = out.read_text(encoding="utf-8")
        modified = original.replace("epochs: 100", "epochs: 999")
        out.write_text(modified, encoding="utf-8")

        assert g.generate(YOLOTrainConfig, out) is False
        assert "epochs: 999" in out.read_text(encoding="utf-8")

    def test_overwrite_true_overrides(self, tmp_path):
        out = tmp_path / "train.yaml"
        out.write_text("epochs: 999\n", encoding="utf-8")
        ConfigGenerator().generate(YOLOTrainConfig, out, overwrite=True)
        assert "epochs: 100" in out.read_text(encoding="utf-8")

    def test_val_generation(self, tmp_path):
        out = tmp_path / "val.yaml"
        ConfigGenerator().generate(YOLOValConfig, out, overwrite=True, title="YOLO 验证配置")
        content = out.read_text(encoding="utf-8")
        assert "split: val"      in content
        assert "conf: 0.001"     in content
        assert "iou: 0.6"        in content
        assert "save_json: true" in content

    def test_creates_parent_dir(self, tmp_path):
        nested = tmp_path / "deep" / "subdir" / "train.yaml"
        assert ConfigGenerator().generate(YOLOTrainConfig, nested, overwrite=True) is True
        assert nested.exists()
