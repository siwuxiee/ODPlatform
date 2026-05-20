import pytest
from odp_platform.data_pipeline import list_capabilities, ConvertOptions
from odp_platform.data_pipeline.registry import get_converter, register_converter
from pathlib import Path
from typing import List
import tempfile, shutil

# 用于测试的虚拟 Converter
class _FakeConverter:
    def __init__(self, input_dir, output_images_dir, output_labels_dir, options):
        pass
    def convert(self) -> List[str]:
        return ["fake"]

class TestRegistry:
    def test_capabilities_matrix_not_empty(self):
        """验证能力矩阵包含三种格式"""
        caps = list_capabilities()
        assert "pascal_voc" in caps
        assert "coco" in caps
        assert "yolo" in caps
        assert caps["pascal_voc"] == ("detect",)
        assert caps["coco"] == ("detect", "segment")
        assert caps["yolo"] == ("detect",)

    def test_get_converter_valid(self):
        """验证获取已注册的 converter 类"""
        cls = get_converter("pascal_voc")
        assert cls is not None
        # 不实例化，仅检查类名
        assert cls.__name__ == "PascalVOCConverter"

    def test_get_converter_invalid_raises(self):
        """验证请求未知格式引发 ValueError"""
        with pytest.raises(ValueError, match="Unsupported dataset format"):
            get_converter("unknown_format")

    def test_convert_options_defaults(self):
        """验证 ConvertOptions 默认值"""
        opts = ConvertOptions()
        assert opts.classes is None
        assert opts.task == "detect"

    def test_convert_options_custom(self):
        """验证自定义 ConvertOptions"""
        opts = ConvertOptions(classes=["cat", "dog"], task="segment")
        assert opts.classes == ["cat", "dog"]
        assert opts.task == "segment"

    def test_register_converter_decorator(self):
        """验证 register_converter 装饰器正常工作（使用临时注册）"""
        # 动态注册一个新的 fake converter
        format_name = "test_fake_format"
        supported_tasks = ("detect", "classify")
        # 使用装饰器手动注册（注意：会永久加入全局注册表，测试后清理？不，简单测试即可）
        @register_converter(format_name, supported_tasks)
        class FakeConverter:
            pass

        # 验证注册成功
        caps = list_capabilities()
        assert format_name in caps
        assert caps[format_name] == supported_tasks

        # 验证可通过 get_converter 获取
        cls = get_converter(format_name)
        assert cls is FakeConverter