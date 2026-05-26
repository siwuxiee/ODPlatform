# ADR-006: training 子系统设计

- **状态**: Accepted
- **日期**: 2026-05-26
- **决策者**: ODPlatform team
- **关联**: ADR-001 (路径 SSoT), ADR-002 (词汇 SSoT), ADR-004 (data_validation), ADR-005 (runtime_config 子系统)

## 1. 背景

D5 完成 runtime_config 子系统后, ODPlatform 已经能:
- 通过 `build_train_config(yaml_path, cli_args)` 得到合并好的 Pydantic 配置 + 溯源 merger
- 通过 `odp-gen-config train` 生成自解释的 YAML 模板
- 通过 D4 `validate_dataset` 对数据集做 fail-fast 校验
- 通过 D2 `get_logger("odp_platform", "train")` 拿到一份"业务模块统一发声"的根 logger

但这些子系统**互相之间没有衔接**——用户拿到配置, 想跑训练, 必须自己写胶水代码约 200 行, 错误率非常高。

## 2. 决策

立一个 `training/` 子系统作为编排器, 把 D2/D4/D5/ultralytics 四方串起来。子系统内部结构遵循"跨任务通用 → `common/`, 训练专属 → `training/`"原则。

### 2.1 核心设计选择

| 决策点 | 选项 | 选择 | 理由 |
|---|---|---|---|
| **service 模式** | 包装器 / 薄壳函数 / 编排器 | **编排器** | 8 阶段流水线, 每阶段调一个邻居子系统 |
| **service 抛不抛异常** | 抛 / 不抛 | **不抛, 装进 `TrainResult.error`** | jupyter / 服务化 / 自动化脚本统一收益 |
| **6 个跨任务工具放哪** | training / common / 新立 yolo_common | **`common/`** | D7 ValService / D8 InferService 都要复用 |
| **TrainMetrics 物理位置** | training/result.py / common/result.py | **`common/result.py`** | D7 ValMetrics 跟 TrainMetrics 几乎同构 |
| **TrainMetrics 公开路径** | 只 common / common + training 转再导出 | **两条路径都暴露** | `from odp_platform.training import TrainMetrics` 符合直觉 |
| **logging handler 装在哪** | 业务模块装 / 每个 service 装 / 只 CLI 入口装 | **只 CLI 入口装一次** | 走 D2 `get_logger("odp_platform", "train")` |
| **log_rename 操作哪个 root** | unnamed root / `"odp_platform"` named root | **named root** | D2 设计了 named root + `propagate=False` |
| **best/last.pt 归档** | 不归档 / 移动 / 复制 | **复制** | 原文件留给 ultralytics resume, 归档一份给 D7/D8 |
| **archive 失败影响 result.success** | 是 / 否 | **否(best-effort)** | 训练已成功, 归档失败只是用户需手动复制 |
| **audit JSON 落点** | runs/<task>_train/<train_dir>/odp_audit.json / 独立目录 | **跟 ultralytics save_dir 同目录** | 跟 args.yaml / results.csv 一起, 自然形成实验快照 |

### 2.2 公开 API (`training/__init__.py` 的 `__all__`)

```python
__all__ = [
    "TrainService",     # class — 训练编排
    "TrainResult",      # dataclass — 训练结果(成败 + 路径 + 指标)
    "TrainMetrics",     # dataclass — 完整指标(转再导出自 common.result)
    "train_yolo",       # function — 便捷一行调用
]
```

### 2.3 3 条工程规矩 (CI 守门)

| 规矩 | grep 自检 |
|---|---|
| service 内部不重新发明 D5 | `grep "YAMLLoader\|CLILoader\|ConfigMerger" service.py` → 0 |
| 业务模块不挂 handler | `grep -rn "addHandler\|setLevel(" training/ common/` → 仅 logging_utils / log_rename |
| 验证/推理子系统不依赖训练 | `grep -rn "from odp_platform.training" evaluation/ inference/` → 0 |

## 3. 不选择的方案

### 方案 A: 把 6 个 common 工具放 `training/`

**为什么不选**: D7 ValService 需要 `resolve_model_path / resolve_dataset_path / rename_log_to_save_dir`, 路径 `from odp_platform.training import resolve_model_path` 名字跟语义打架。

### 方案 B: 立一层 `yolo_common/` 隔离 YOLO 工具

**为什么不选**: `odp_platform` 这个端的定位就是"目标检测平台"——`common/` 必然被 YOLO 概念污染, 那是合理的。再加一层等于在 YOLO 平台里加一个"yolo 子标签", 跟项目名打架。

### 方案 C: 把整个 D6 揉成一个 `train.py` 朴素脚本

**为什么不选**: D5 立的配置溯源、D4 立的数据校验、D2 立的 logging 通道全部要在用户那一侧手工拼接, 每用户写 200 行胶水代码, 错误率高。

### 方案 D: 不立 log_rename, 只靠 `audit JSON` 记录 log_path

**为什么不选**: `ls logging/train/` 跟 `ls runs/detect_train/` 对不上是真实高频痛点。文件名直接编码 save_dir 比 audit JSON 查映射的体验好得多。log_rename 的风险用"操作 named root + best-effort 永不抛 + 失败回滚"治住了。

## 4. 后果

### 4.1 好处

- **一行 `odp-train` 跑通完整训练**, 自动接 D2/D4/D5/ultralytics
- **`TrainResult` 永不抛**——jupyter / 服务化 / 自动化脚本调用方式统一
- **`common/` 6 个工具直接被 D7/D8 复用**——维护成本低
- **`odp_audit.json` 给未来 experiment_db 留好落点**
- **日志文件名跟 save_dir 对得上**——日常 debug 不再查映射表

### 4.2 风险

- **`training/__init__.py` 转再导出 `TrainMetrics`**——一个符号两个路径, 靠 ADR + docstring 解释
- **log_rename 操作 named root**——D2 改了 `ROOT_LOGGER_NAME` 常量需同步修改(源码注释已标注)
- **archive 失败不影响 `success`**——用户可能错过 warning, 缓解: warning 级输出 + audit JSON `best_archive` 字段 null

## 5. 关键文件位置

```
apps/platform/src/odp_platform/

common/                              ← 跨任务通用 (6 个新增)
├── model_path.py                    resolve_model_path (含 search_dirs)
├── dataset_path.py                  resolve_dataset_path
├── log_rename.py                    rename_log_to_save_dir (操作 named root)
├── config_log.py                    log_effective_config + log_override_chains
├── result.py                        TrainMetrics + log_train_metrics
└── plot_style.py                    apply_academic_style

training/                            ← 训练专属 (3 个新增)
├── __init__.py                      公开 4 个符号
├── service.py                       TrainService + TrainResult + train_yolo
└── archive.py                       archive_checkpoints

cli/                                 ← CLI 入口 (1 个新增)
└── train_model.py                   odp-train

tests/                               ← 单元测试 (9 个新增)
├── common/
│   ├── conftest.py                  mock_det_results / mock_segment_results
│   ├── test_model_path.py
│   ├── test_dataset_path.py
│   ├── test_log_rename.py
│   ├── test_config_log.py
│   └── test_result.py
└── training/
    ├── conftest.py                  fake_train_dir
    ├── test_archive.py
    └── test_service.py
```

## 6. 跟其他 ADR 的关系

- **ADR-001 (路径 SSoT)**: D6 完全靠 `common/paths.py` 拿路径, 不动它
- **ADR-002 (词汇 SSoT)**: D6 完全靠 `common/constants.py` 的 `Task.DETECT / Task.SEGMENT`
- **ADR-004 (data_validation)**: D6 通过 `validate_dataset` + `render_to_logger` 调用 D4
- **ADR-005 (runtime_config)**: D6 通过 `build_train_config(yaml_path, cli_args)` 一行获取配置和 merger

## 7. 后续工作

- **D7: evaluation 子系统** — 立 ValService, 复用 D6 的 6 个 common 工具
- **D8: inference 子系统** — 立 InferService, 同样复用 6 个 common 工具
- **experiment_db 子系统(尚未编号)** — 接管 `odp_audit.json` 的消费侧

## 8. 修订记录

- **2026-05-26**: 初版 (Accepted)
