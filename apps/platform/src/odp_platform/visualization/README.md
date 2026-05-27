# visualization

> YOLO 检测结果美化绘制模块 —— 圆角检测框 + 中英文标签 + 标签映射 + 文本尺寸预计算缓存。
> 把"画框 + 写字"这件高频但繁琐的事彻底封装,业务方一行 `draw()` 即可。

## 30 秒上手

```python
from visualization import BeautifyVisualizer, Detection

viz = BeautifyVisualizer(
    labels=["person", "car"],
    label_mapping={"person": "人员", "car": "汽车"},
    color_mapping={"person": (0, 255, 0), "car": (255, 0, 0)},
)

# 从 YOLO 结果创建 Detection 列表
detections = BeautifyVisualizer.from_yolo_results(
    boxes=boxes.xyxy.cpu().numpy(),
    confidences=boxes.conf.cpu().numpy(),
    labels=labels,
)

# 美化绘制(自适应图像尺寸)
annotated = viz.draw(frame, detections, use_label_mapping=True)
```

如果**不需要美化**(中文 / 圆角 / 标签映射),直接用 YOLO 原生 `results[0].plot()` 即可,不必引入本模块。

## 安装

```bash
pip install -r requirements.txt
```

或直接装:

```bash
pip install "numpy>=1.20" "opencv-python>=4.5" "Pillow>=9.0" "pydantic>=2.0"
```

字体单独放(开源、商用免费):

```
visualization/assets/LXGWWenKai-Bold.ttf
```

下载: <https://github.com/lxgw/LxgwWenKai/releases>

## 可拷贝性(核心理念)

**整个 `visualization/` 目录可整包拷贝到任何 Python 项目下使用**,不依赖宿主项目的任何内部基础设施:

- 模块内 `__init__.py` / 子模块全部使用相对导入(`from .core ...`),包路径变了也不炸
- 字体走模块内置路径 `visualization/assets/`,跟随模块走,不靠 CWD
- 数据类型 / 配置 / 工具类全部模块内自洽,不引用宿主项目代码

拷贝示例:

```bash
# 拷到 your_project/utils/ 下
cp -r visualization your_project/utils/

# 调用方零改动:
from your_project.utils.visualization import BeautifyVisualizer
```

## 模块结构

```
visualization/
├── __init__.py             # 公共 API
├── visualizer.py           # 主类 BeautifyVisualizer
├── core/                   # 核心组件
│   ├── __init__.py
│   ├── data_types.py       # Detection / DrawStyle(Pydantic) / LabelLayout
│   ├── text_cache.py       # 文本尺寸预计算缓存
│   ├── draw_utils.py       # RoundedRect / LayoutCalculator
│   └── renderers.py        # PillowTextRenderer
├── assets/                 # 模块内置资源(字体)
│   └── LXGWWenKai-Bold.ttf
├── requirements.txt
├── .gitignore
└── README.md
```

## 设计纪律

对齐 `frame_source` 模块,共四条:

| 原则 | 在本模块的兑现 |
|---|---|
| 统一接口 | 任意 YOLO 检测结果 → 同一个 `draw()` 入口 |
| 关注点分离 | 数据(`data_types`) / 缓存(`text_cache`) / 绘制(`draw_utils`) / 渲染(`renderers`) 各管一段 |
| 自给自足 | 字体内置,数据类型自定义,不引用任何宿主项目 |
| 显式回退 | 字体加载失败 → `logger.warning` 告知后果与修复建议,而非静默 fallback |

## 几个关键修复点

如果你来自旧版本,以下点已修复:

1. **字体路径不再用裸文件名** —— 默认走模块内置 `assets/`,绝对路径解析,不靠 CWD
2. **字体加载失败不再静默** —— 显式 `logger.warning` + 用 PIL 默认字体回退,程序继续可用;warning 只发一次(不刷屏)
3. **`DrawStyle` 改用 Pydantic v2** —— 字号 / padding / radius / BGR 颜色全部带字段约束,typo 字段立刻 `ValidationError`
4. **文件头不再写死 `utils/` 前缀** —— 拷到任何包路径下都不需要改

## 许可证

跟随宿主项目。
