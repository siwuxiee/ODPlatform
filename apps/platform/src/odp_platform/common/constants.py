# apps/platform/src/odp_platform/common/constants.py

"""
全局共享常量定义 (Shared Vocabulary)
"""


class Task:
    DETECT = "detect"
    SEGMENT = "segment"
    CLASSIFY = "classify"

    @classmethod
    def choices(cls):
        return (cls.DETECT, cls.SEGMENT, cls.CLASSIFY)

    @classmethod
    def all(cls):
        """D5 SSoT: 用于运行时配置的 task 字段 validator 封闭取值."""
        return set(cls.choices())


# 任务类型 (保留向后兼容的模块级常量)
TASK_DETECT = Task.DETECT
TASK_SEGMENT = Task.SEGMENT
TASK_CLASSIFY = Task.CLASSIFY

# 数据集划分
SPLIT_TRAIN = "train"
SPLIT_VAL = "val"
SPLIT_TEST = "test"

# 支持的数据集格式
FORMAT_PASCAL_VOC = "pascal_voc"
FORMAT_COCO = "coco"
FORMAT_YOLO = "yolo"

# 支持的图像扩展名
IMAGE_EXTENSIONS: set[str] = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}

# D4: pair_existence check 阈值
PAIR_MISSING_ERROR_RATIO: float = 0.5
PAIR_MISSING_WARN_RATIO: float = 0.05