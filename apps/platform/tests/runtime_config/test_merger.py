#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""ConfigMerger + ConfigMetadata 链表溯源."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from odp_platform.runtime_config.train  import YOLOTrainConfig
from odp_platform.runtime_config.merger import (
    ConfigMerger, ConfigSource, ConfigMetadata,
)


# ============================================================
# 优先级: CLI > YAML > DEFAULT
# ============================================================

class TestPriority:
    def test_cli_overrides_yaml(self):
        m = ConfigMerger()
        c = m.merge(YOLOTrainConfig, sources=[
            (ConfigSource.YAML, {"epochs": 200}),
            (ConfigSource.CLI,  {"epochs": 300}),
        ])
        assert c.epochs == 300

    def test_yaml_overrides_default(self):
        m = ConfigMerger()
        c = m.merge(YOLOTrainConfig, sources=[(ConfigSource.YAML, {"epochs": 50})])
        assert c.epochs == 50

    def test_default_falls_through(self):
        m = ConfigMerger()
        c = m.merge(YOLOTrainConfig)
        assert c.epochs == 100

    def test_partial_overrides(self):
        m = ConfigMerger()
        c = m.merge(YOLOTrainConfig, sources=[
            (ConfigSource.YAML, {"epochs": 200, "batch": 32, "lr0": 0.005}),
            (ConfigSource.CLI,  {"epochs": 300}),
        ])
        assert c.epochs == 300
        assert c.batch  == 32
        assert c.lr0    == 0.005
        assert c.workers == 8


# ============================================================
# 链表溯源
# ============================================================

class TestChain:
    def test_three_layer_chain(self):
        m = ConfigMerger()
        m.merge(YOLOTrainConfig, sources=[
            (ConfigSource.YAML, {"epochs": 200}),
            (ConfigSource.CLI,  {"epochs": 300}),
        ])
        meta = m.get_metadata("epochs")
        chain = meta.chain()
        assert len(chain) == 3
        assert chain[0].value == 300 and chain[0].source == ConfigSource.CLI
        assert chain[1].value == 200 and chain[1].source == ConfigSource.YAML
        assert chain[2].value == 100 and chain[2].source == ConfigSource.DEFAULT

    def test_two_layer_chain(self):
        m = ConfigMerger()
        m.merge(YOLOTrainConfig, sources=[(ConfigSource.YAML, {"epochs": 200})])
        chain = m.get_metadata("epochs").chain()
        assert len(chain) == 2
        assert chain[0].source == ConfigSource.YAML
        assert chain[1].source == ConfigSource.DEFAULT

    def test_one_layer_chain_for_untouched_default(self):
        m = ConfigMerger()
        m.merge(YOLOTrainConfig)
        chain = m.get_metadata("epochs").chain()
        assert len(chain) == 1
        assert chain[0].source == ConfigSource.DEFAULT

    def test_chain_str_format(self):
        m = ConfigMerger()
        m.merge(YOLOTrainConfig, sources=[
            (ConfigSource.YAML, {"lr0": 0.005}),
            (ConfigSource.CLI,  {"lr0": 0.001}),
        ])
        meta = m.get_metadata("lr0")
        assert "0.001(CLI)" in meta.chain_str()
        assert "0.005(YAML)" in meta.chain_str()
        assert "0.01(DEFAULT)" in meta.chain_str()


# ============================================================
# 报告
# ============================================================

class TestReports:
    def test_source_report_groups_by_source(self):
        m = ConfigMerger()
        m.merge(YOLOTrainConfig, sources=[
            (ConfigSource.YAML, {"epochs": 200, "batch": 32}),
            (ConfigSource.CLI,  {"lr0": 0.001}),
        ])
        report = m.get_source_report()
        assert "CLI (1 项)"  in report
        assert "YAML (2 项)" in report
        assert "DEFAULT"     in report

    def test_conflict_report_shows_chain(self):
        m = ConfigMerger()
        m.merge(YOLOTrainConfig, sources=[
            (ConfigSource.YAML, {"epochs": 200, "lr0": 0.005}),
            (ConfigSource.CLI,  {"epochs": 300}),
        ])
        report = m.get_conflict_report()
        assert "200 (YAML)" in report
        assert "300 (CLI)" in report
        assert "0.01 (DEFAULT)" in report
        assert "0.005 (YAML)" in report


# ============================================================
# ValidationError source tracking
# ============================================================

class TestValidationErrorSourceInfo:
    def test_source_info_after_validation_error(self):
        """ValidationError 时可通过 merger.last_validation_source_info 获取来源链."""
        m = ConfigMerger()
        with pytest.raises(ValidationError):
            m.merge(YOLOTrainConfig, sources=[(ConfigSource.YAML, {"epochs": -5})])
        source_info = m.last_validation_source_info
        assert "epochs" in source_info
        assert "-5(YAML)" in source_info["epochs"]
        assert "100(DEFAULT)" in source_info["epochs"]

    def test_track_sources_false_no_source_info(self):
        m = ConfigMerger(track_sources=False)
        with pytest.raises(ValidationError):
            m.merge(YOLOTrainConfig, sources=[(ConfigSource.YAML, {"epochs": -5})])
        assert m.last_validation_source_info == {}


# ============================================================
# 边界
# ============================================================

class TestEdgeCases:
    def test_none_does_not_override(self):
        m = ConfigMerger()
        c = m.merge(YOLOTrainConfig, sources=[
            (ConfigSource.YAML, {"epochs": 50}),
            (ConfigSource.CLI,  {"epochs": None}),
        ])
        assert c.epochs == 50

    def test_merger_reusable(self):
        m = ConfigMerger()
        m.merge(YOLOTrainConfig, sources=[(ConfigSource.YAML, {"epochs": 100})])
        assert m.get_metadata("epochs").value == 100

        m.merge(YOLOTrainConfig, sources=[(ConfigSource.CLI, {"epochs": 200})])
        assert m.get_metadata("epochs").value  == 200
        assert m.get_metadata("epochs").source == ConfigSource.CLI
        chain = m.get_metadata("epochs").chain()
        assert all(meta.source != ConfigSource.YAML for meta in chain)

    def test_track_sources_disabled(self):
        m = ConfigMerger(track_sources=False)
        c = m.merge(YOLOTrainConfig, sources=[(ConfigSource.YAML, {"epochs": 77})])
        assert c.epochs == 77
        assert m.get_metadata("epochs") is None
        assert "未启用" in m.get_source_report()
