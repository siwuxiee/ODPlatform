# ODPlatform — 通用目标检测开发平台

ODPlatform 是一个面向 YOLO 系列模型的通用目标检测开发平台，提供从**数据准备、模型训练、评估到推理部署**的完整工具链。平台采用 Python 开发，基于 [Ultralytics](https://github.com/ultralytics/ultralytics) 框架，支持命令行接口（CLI）和 PySide6 桌面客户端两种交互方式。

## ✨ 主要特性

- **模块化架构** — 十余个独立子系统，职责清晰、边界明确，可独立开发与测试
- **全流程自动化** — 从原始数据集转换到模型推理结果可视化，均可通过 CLI 一键完成
- **多格式数据兼容** — 支持 COCO、Pascal VOC、YOLO 三种主流标注格式的相互转换
- **强类型配置管理** — 基于 Pydantic v2，采用"YAML 默认配置 → 项目级覆盖 → CLI 参数"三层合并策略
- **高性能推理引擎** — 多线程流水线架构，将帧捕获、模型推理、渲染绘制解耦为独立线程
- **图形化桌面客户端** — 基于 PySide6，集成实时检测画面显示、模型/数据源切换和结果统计
- **完整审计追溯** — 训练与推理均自动生成 `odp_audit.json`，记录完整配置快照和指标数据

## 🏗️ 项目结构

```
ODPlatform/
├── apps/
│   ├── platform/                 # 核心引擎（CLI + 所有功能模块）
│   │   ├── src/odp_platform/
│   │   │   ├── common/           # 公共基础设施（路径、日志、结果类型、系统工具）
│   │   │   ├── cli/              # CLI 命令入口（odp-train, odp-infer 等）
│   │   │   ├── data_pipeline/    # 数据管道（格式转换、数据集划分）
│   │   │   ├── data_validation/  # 数据校验（完整性、格式、唯一性检查）
│   │   │   ├── runtime_config/   # 运行时配置（Pydantic 模型 + 三层合并）
│   │   │   ├── training/         # 训练模块（8 阶段训练编排器）
│   │   │   ├── evaluation/       # 评估模块（mAP/Precision/Recall 等指标）
│   │   │   ├── inference/        # 推理加速（多线程流水线引擎）
│   │   │   ├── frame_source/     # 帧源抽象（摄像头/视频/图片统一接口）
│   │   │   └── visualization/    # 可视化（自定义绘制、中文标签渲染）
│   │   └── tests/                # 单元测试 & 集成测试
│   └── desktop/                  # PySide6 桌面客户端
│       └── src/odp_desktop/
│           └── widgets/          # UI 组件（控制面板、画面显示、结果面板）
├── packages/
│   └── shared-schemas/           # 跨项目共享 Schema
├── scripts/                      # 辅助脚本（项目初始化/重置）
├── tests/                        # 顶层集成测试
├── docs/                         # 文档
└── pyproject.toml                # Workspace 级工具配置
```

## 📦 模块说明

| 模块 | 说明 |
|------|------|
| **common** | 路径解析、日志系统、模型/数据集路径查找、结构化结果类型、性能工具 |
| **cli** | 各核心功能的 CLI 入口，负责参数解析、日志初始化并调用对应服务 |
| **data_pipeline** | COCO / Pascal VOC / YOLO 格式互转，数据集划分，生成 data.yaml |
| **data_validation** | YAML schema 校验、图片-标签配对、标注格式验证、跨集合唯一性检查 |
| **runtime_config** | Pydantic v2 强类型配置，三层合并，配置模板生成 |
| **training** | 8 阶段训练编排器（TrainService），集成校验、训练、归档、审计 |
| **evaluation** | 模型验证评估，输出 mAP@50、mAP@50-95、Precision、Recall 等指标 |
| **inference** | 多线程流水线推理引擎（ThreadedPipeline），捕获→推理→渲染解耦 |
| **frame_source** | 统一的帧源接口，支持摄像头、视频文件、图片目录，工厂模式创建 |
| **visualization** | 自定义美化可视化叠加层（BeautifyVisualizer），支持中文渲染 |
| **desktop** | PySide6 图形界面，集成控制面板、实时画面、源切换和结果保存 |

## 🚀 快速开始

### 环境要求

- **Python** ≥ 3.11
- **操作系统**: Linux（推荐）、Windows、macOS
- **GPU**: 支持 CUDA 的 NVIDIA GPU（训练和推理加速，可选，CPU 也可运行推理）

### 安装

```bash
# 克隆仓库
git clone <repo-url>
cd ODPlatform

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate

# 安装核心平台
pip install -e apps/platform

# 安装桌面客户端（可选）
pip install -e apps/desktop

# 安装开发依赖（可选）
pip install -e ".[dev]"
```

### CLI 命令

| 命令 | 说明 |
|------|------|
| `odp-init` | 初始化项目工作区 |
| `odp-reset` | 重置项目状态 |
| `odp-transform` | 数据集格式转换与划分 |
| `odp-validate` | 数据集完整性校验 |
| `odp-gen-config` | 生成配置模板文件 |
| `odp-train` | 启动模型训练 |
| `odp-val` | 模型评估验证 |
| `odp-infer` | 模型推理（支持摄像头/视频/图片） |
| `odp-desktop` | 启动桌面客户端 |

### 典型工作流

```bash
# 1. 初始化项目
odp-init

# 2. 转换数据集并划分
odp-transform --source ./raw_data --format coco --ratio 0.7 0.2 0.1

# 3. 校验数据集
odp-validate

# 4. 生成训练配置
odp-gen-config train -o train_config.yaml

# 5. 训练模型
odp-train --model yolo11n.pt --data data.yaml --epochs 100 --device 0

# 6. 评估模型
odp-val --model runs/detect_train/<exp>/weights/best.pt

# 7. 推理测试
odp-infer --model models/checkpoints/best.pt --source 0          # 摄像头
odp-infer --model models/checkpoints/best.pt --source video.mp4  # 视频文件
odp-infer --model models/checkpoints/best.pt --source ./images/  # 图片目录

# 8. 启动桌面客户端
odp-desktop
```

## 🔧 技术栈

| 类别 | 技术 |
|------|------|
| 深度学习框架 | Ultralytics YOLO (v8 / v11)、PyTorch |
| 配置管理 | Pydantic v2、YAML |
| CLI | argparse |
| 图形界面 | PySide6 (Qt for Python) |
| 图像处理 | OpenCV |
| 代码质量 | Ruff、Mypy、pytest |
| 构建工具 | Hatchling |
| 包管理 | pip (editable installs) |

## 📊 支持的模型与任务

- **模型系列**: YOLOv8、YOLO11
- **模型规格**: nano / small / medium / large / xlarge
- **任务类型**: 目标检测（detect）、实例分割（segment）、图像分类（classify）
- **预训练权重**: 自动从 Ultralytics 官方仓库下载，也支持本地自定义预训练模型

## 🎨 可视化

BeautifyVisualizer 提供增强的可视化能力：

- 中文标签渲染（Pillow 文本缓存，避免逐帧重绘）
- 自定义颜色映射与标签映射
- 样式化检测框（圆角、阴影、置信度条）
- 完全替代 YOLO 原生绘制，效果更美观

## 🧪 测试

```bash
# 运行全部测试
pytest

# 仅运行单元测试
pytest -m unit

# 运行特定模块测试
pytest apps/platform/tests/data_pipeline/
pytest apps/platform/tests/runtime_config/
```

## 📄 License

MIT License
