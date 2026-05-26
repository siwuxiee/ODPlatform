"""config_log 单元测试."""
from __future__ import annotations

import logging
from unittest.mock import MagicMock

from odp_platform.common.config_log import (
    _safe_get_metadata,
    log_effective_config,
    log_override_chains,
)


def test_log_effective_config_reads_each_field(caplog):
    """每个字段输出一行 + 来源."""
    caplog.set_level(logging.INFO)
    fake_config = MagicMock()
    fake_config.__class__.model_fields = {"epochs": ..., "batch": ..., "lr0": ...}
    fake_config.epochs = 100
    fake_config.batch = 16
    fake_config.lr0 = 0.01

    fake_merger = MagicMock()
    fake_merger.get_metadata = MagicMock(
        side_effect=lambda n: MagicMock(source_label="CLI")
    )

    log_effective_config(fake_config, fake_merger)
    assert "epochs" in caplog.text
    assert "100" in caplog.text
    assert "CLI" in caplog.text


def test_log_effective_config_handles_mixed_sources(caplog):
    """不同字段不同来源标签."""
    caplog.set_level(logging.INFO)
    fake_config = MagicMock()
    fake_config.__class__.model_fields = {"a": ..., "b": ...}
    fake_config.a = 1
    fake_config.b = 2

    call_count = [0]

    def _meta(name):
        call_count[0] += 1
        m = MagicMock()
        m.source_label = "YAML" if name == "a" else "DEFAULT"
        return m

    fake_merger = MagicMock()
    fake_merger.get_metadata = MagicMock(side_effect=_meta)

    log_effective_config(fake_config, fake_merger)
    assert "YAML" in caplog.text
    assert "DEFAULT" in caplog.text


def test_log_override_chains_reverse_order(caplog):
    """chain 显示按 DEFAULT → CLI 方向(reverse D5 chain)."""
    caplog.set_level(logging.INFO)
    fake_config = MagicMock()
    fake_config.__class__.model_fields = {"lr0": ...}
    fake_config.lr0 = 0.001

    # 构造 3 链: D5 newest-first [CLI:0.001, YAML:0.01, DEFAULT:0.01]
    chain_mock = [
        MagicMock(value=0.001, source_label="CLI"),
        MagicMock(value=0.01, source_label="YAML"),
        MagicMock(value=0.01, source_label="DEFAULT"),
    ]
    meta = MagicMock()
    meta.chain.return_value = chain_mock

    fake_merger = MagicMock()
    fake_merger.get_metadata = MagicMock(return_value=meta)

    log_override_chains(fake_config, fake_merger)
    # oldest-first: DEFAULT:0.01 <- YAML:0.01 <- CLI:0.001
    text = caplog.text
    idx_default = text.index("DEFAULT")
    idx_yaml = text.index("YAML")
    idx_cli = text.index("CLI")
    assert idx_default < idx_yaml < idx_cli


def test_safe_get_metadata_returns_none_for_mock_without_method(caplog):
    """merger 没 get_metadata — 不崩, 字段仍打印."""
    caplog.set_level(logging.INFO)
    fake_config = MagicMock()
    fake_config.__class__.model_fields = {"epochs": ...}
    fake_config.epochs = 100

    bad_merger = object()  # 完全没 get_metadata
    log_effective_config(fake_config, bad_merger)
    assert "epochs" in caplog.text  # 字段仍然打了


def test_safe_get_metadata_returns_none_on_exception():
    """merger.get_metadata 抛异常 — 返回 None, 不崩."""
    bad_merger = MagicMock()
    bad_merger.get_metadata = MagicMock(side_effect=RuntimeError("boom"))
    assert _safe_get_metadata(bad_merger, "epochs") is None


def test_safe_get_metadata_no_get_metadata_attr():
    """没有 get_metadata 属性 — 返回 None."""
    assert _safe_get_metadata(object(), "epochs") is None
