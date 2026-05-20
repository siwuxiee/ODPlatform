# apps/platform/src/odp_platform/data_pipeline/service.py

from pathlib import Path
from typing import Optional, List
from .registry import get_converter, ConvertOptions

def convert_dataset(
    format_name: str,
    input_dir: Path,
    output_images_dir: Path,
    output_labels_dir: Path,
    options: Optional[ConvertOptions] = None
) -> List[str]:
    """
    调度层：获取对应的 converter 并执行转换。
    返回该数据集实际包含的类别列表。
    """
    if options is None:
        options = ConvertOptions()
        
    converter_class = get_converter(format_name)
    # 实例化 converter
    converter = converter_class(input_dir, output_images_dir, output_labels_dir, options)
    # 执行转换并返回类别列表
    return converter.convert()