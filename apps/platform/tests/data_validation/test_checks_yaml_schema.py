import tempfile
from pathlib import Path

import pytest
import yaml

from odp_platform.data_validation import CheckContext, CheckSeverity
from odp_platform.data_validation.checks.yaml_schema import validate_yaml_schema


def _write_yaml(path: Path, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f)


def test_valid_yaml_passes(tmp_path: Path):
    yaml_path = tmp_path / "valid.yaml"
    _write_yaml(yaml_path, {"nc": 2, "names": ["cat", "dog"], "train": "train", "val": "val"})
    result = validate_yaml_schema(CheckContext(yaml_path=yaml_path))
    assert result.severity == CheckSeverity.PASS


def test_file_not_found(tmp_path: Path):
    yaml_path = tmp_path / "nonexistent.yaml"
    result = validate_yaml_schema(CheckContext(yaml_path=yaml_path))
    assert result.severity == CheckSeverity.ERROR
    assert "file_not_found" in result.details["problems"]


def test_parse_error(tmp_path: Path):
    yaml_path = tmp_path / "bad.yaml"
    yaml_path.write_text(": : : bad: yaml: ::", encoding="utf-8")
    result = validate_yaml_schema(CheckContext(yaml_path=yaml_path))
    assert result.severity == CheckSeverity.ERROR
    assert "parse_error" in result.details["problems"]


def test_top_level_not_dict(tmp_path: Path):
    yaml_path = tmp_path / "list.yaml"
    yaml_path.write_text("- item1\n- item2\n", encoding="utf-8")
    result = validate_yaml_schema(CheckContext(yaml_path=yaml_path))
    assert result.severity == CheckSeverity.ERROR
    assert "top_level_not_dict" in result.details["problems"]


def test_missing_nc(tmp_path: Path):
    yaml_path = tmp_path / "no_nc.yaml"
    _write_yaml(yaml_path, {"names": ["a", "b"]})
    result = validate_yaml_schema(CheckContext(yaml_path=yaml_path))
    assert result.severity == CheckSeverity.ERROR
    problems = result.details["problems"]
    assert any("缺少 'nc'" in p for p in problems)


def test_nc_names_length_mismatch(tmp_path: Path):
    yaml_path = tmp_path / "mismatch.yaml"
    _write_yaml(yaml_path, {"nc": 3, "names": ["a", "b"]})
    result = validate_yaml_schema(CheckContext(yaml_path=yaml_path))
    assert result.severity == CheckSeverity.ERROR
    problems = result.details["problems"]
    assert any("不一致" in p for p in problems)


def test_collects_multiple_problems(tmp_path: Path):
    yaml_path = tmp_path / "multi.yaml"
    _write_yaml(yaml_path, {"nc": -1, "names": [1, 2]})
    result = validate_yaml_schema(CheckContext(yaml_path=yaml_path))
    assert result.severity == CheckSeverity.ERROR
    problems = result.details["problems"]
    assert len(problems) >= 2


def test_names_dict_form(tmp_path: Path):
    yaml_path = tmp_path / "dict_names.yaml"
    _write_yaml(yaml_path, {"nc": 2, "names": {0: "cat", 1: "dog"}})
    result = validate_yaml_schema(CheckContext(yaml_path=yaml_path))
    assert result.severity == CheckSeverity.PASS
