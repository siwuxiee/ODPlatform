# apps/platform/src/odp_platform/data_pipeline/registry.py

from dataclasses import dataclass
from typing import Optional, List, Dict, Tuple, Type, Any

@dataclass
class ConvertOptions:
    """
    转换选项。
    classes: 若为 None，表示自动从数据集中推断类别；若提供 List[str]，则按提供的类别过滤/排序。
    """
    classes: Optional[List[str]] = None

# 注册表字典：格式名称 -> (支持的任务元组, 转换器类)
_REGISTRY: Dict[str, Tuple[Tuple[str, ...], Type[Any]]] = {}
_INITIALIZED = False

def _lazy_init():
    """延迟初始化，避免循环导入，并确保所有 converter 被注册"""
    global _INITIALIZED
    if _INITIALIZED:
        return
    
    # 这里的模块在阶段 2, 3, 4 会依次创建，IDE 报错请忽略，不要注释！
    import odp_platform.data_pipeline.core.pascal_voc
    import odp_platform.data_pipeline.core.coco
    import odp_platform.data_pipeline.core.yolo
    
    _INITIALIZED = True

def register_converter(format_name: str, supported_tasks: Tuple[str, ...]):
    """装饰器：用于将 Converter 注册到注册表中"""
    def decorator(cls):
        _REGISTRY[format_name] = (supported_tasks, cls)
        return cls
    return decorator

def get_converter(format_name: str) -> Type[Any]:
    """根据格式名称获取对应的 Converter 类"""
    _lazy_init()
    if format_name not in _REGISTRY:
        raise ValueError(f"Unsupported dataset format: {format_name}")
    return _REGISTRY[format_name][1]

def list_capabilities() -> Dict[str, Tuple[str, ...]]:
    """返回当前系统支持的格式及其对应的任务能力矩阵"""
    _lazy_init()
    return {fmt: tasks for fmt, (tasks, _) in _REGISTRY.items()}