import pytest
from pathlib import Path
from unittest.mock import patch

from odp_platform.data_validation.registry import (
    CheckSeverity,
    CheckResult,
    CheckContext,
    CheckEntry,
    _REGISTRY,
    check,
    get_all_checks,
)


class TestCheckSeverity:
    def test_rank_ordering(self):
        assert CheckSeverity.rank(CheckSeverity.PASS) < CheckSeverity.rank(CheckSeverity.INFO)
        assert CheckSeverity.rank(CheckSeverity.INFO) < CheckSeverity.rank(CheckSeverity.WARNING)
        assert CheckSeverity.rank(CheckSeverity.WARNING) < CheckSeverity.rank(CheckSeverity.ERROR)

    def test_rank_error_is_highest(self):
        assert CheckSeverity.rank(CheckSeverity.ERROR) == 3

    def test_rank_pass_is_lowest(self):
        assert CheckSeverity.rank(CheckSeverity.PASS) == 0


class TestCheckResult:
    def test_passed_for_pass(self):
        r = CheckResult(name="test", severity=CheckSeverity.PASS, summary="ok", details={})
        assert r.passed is True

    def test_passed_for_info(self):
        r = CheckResult(name="test", severity=CheckSeverity.INFO, summary="ok", details={})
        assert r.passed is True

    def test_not_passed_for_warning(self):
        r = CheckResult(name="test", severity=CheckSeverity.WARNING, summary="warn", details={})
        assert r.passed is False

    def test_not_passed_for_error(self):
        r = CheckResult(name="test", severity=CheckSeverity.ERROR, summary="err", details={})
        assert r.passed is False


class TestCheckDecorator:
    def test_registration(self):
        @check("test_register_unique")
        def dummy(ctx):
            return CheckResult(name="dummy", severity=CheckSeverity.PASS, summary="", details={})

        entries = get_all_checks()
        names = [e.name for e in entries]
        assert "test_register_unique" in names

    def test_duplicate_registration_raises(self):
        @check("test_dup_check")
        def dummy1(ctx):
            return CheckResult(name="d1", severity=CheckSeverity.PASS, summary="", details={})

        with pytest.raises(ValueError, match="already registered"):
            @check("test_dup_check")
            def dummy2(ctx):
                return CheckResult(name="d2", severity=CheckSeverity.PASS, summary="", details={})

    def test_decorator_returns_original_function(self):
        @check("test_returns_original")
        def dummy(ctx):
            return CheckResult(name="dummy", severity=CheckSeverity.PASS, summary="", details={})

        # 装饰器直接返回原函数，不包装
        assert dummy.__name__ == "dummy"


class TestCheckContext:
    def test_default_snapshot_is_none(self):
        ctx = CheckContext(yaml_path=Path("/tmp/test.yaml"))
        assert ctx.snapshot is None

    def test_with_snapshot(self):
        ctx = CheckContext(yaml_path=Path("/tmp/test.yaml"), snapshot="fake_snapshot")
        assert ctx.snapshot == "fake_snapshot"


class TestAutoDiscovery:
    def test_get_all_checks_finds_builtin_checks(self):
        entries = get_all_checks()
        names = {e.name for e in entries}
        assert "yaml_schema" in names
        assert "pair_existence" in names
        assert "label_format" in names
        assert "split_uniqueness" in names

    def test_each_entry_has_callable_func(self):
        entries = get_all_checks()
        for e in entries:
            assert callable(e.func), f"check '{e.name}' func is not callable"
