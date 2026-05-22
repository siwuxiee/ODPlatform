# ADR-004: data_validation 子系统 — check-registry 架构

## 上下文

D3 (`data_pipeline`) 负责把原始数据集转化为 ultralytics 兼容的训练 yaml，但不对产出质量做任何保证。在数据被喂给 D5 训练之前，需要一个独立的质检步骤，回答"这数据能不能训"的问题。

`data_validation` 子系统只检测不修复——发现问题归质检，修复问题归 `data_pipeline` 重跑产线。

## 七大决策

### 1. 注册表聚合执行

D3 registry 是"互斥分发"——一次跑 1 个 converter。D4 registry 是"聚合执行"——一次跑全部 check。

check 之间互相独立：任何一个失败/抛异常都不得阻断其他 check。这由 `service._safe_run_one` 保证，它是整个子系统唯一一处 `except Exception` 宽捕获。

### 2. CheckResult 四字段 + 四级 severity

`CheckResult` 只有 4 个字段：`name`、`severity`、`summary`、`details`。`passed` 是 `@property` 派生值，不存字段。

`CheckSeverity` 是字符串常量类（不用 `enum.Enum`），四级：`PASS < INFO < WARNING < ERROR`。INFO 算 passed（语义：知道一下，不阻断）。

### 3. DatasetSnapshot 一次扫描

`build_snapshot` 对数据集做一次全量扫描，产出不可变的 `DatasetSnapshot`（`frozen=True`，所有容器字段用 `Tuple` 防串改）。四个 check 共享同一个 snapshot，不需要各自重复扫盘。

`build_snapshot` 采用 best-effort 策略——yaml 解析失败不抛，装进 `yaml_load_error` 让 `yaml_schema` check 去报告。

### 4. pkgutil.iter_modules 自动发现

用 `pkgutil.iter_modules` 扫描 `checks/` 子包，import time 触发 `@check` 装饰器副作用完成注册。新增 check = 加新文件，`registry.py` 一行不动。下划线前缀文件被自动跳过留作内部辅助。

### 5. 数据 / 展示分离

`report.py` 装纯数据 + `@property` 派生属性 + `to_dict()`。`render.py` 把 `ValidationReport` 翻译成三段式日志输出。两个文件物理隔离——将来加 HTML / Markdown renderer = 新增文件，数据层不动。

当前不引入 `ReportSection` 中间抽象层（YAGNI）。

### 6. SRP：只检测，不修复

质检子系统不提供 `--fix` 能力。`CheckResult` 不含 `fixable` 字段。发现问题归 `data_validation`，修复问题归 `data_pipeline` 重跑产线。

### 7. validate_dataset 是函数，不是类

`validate_dataset` 是纯函数——内部状态（run_id / duration / snapshot / results）全部进了返回值 `ValidationReport`。没有第二个相关公共方法，做成类是 OOP 仪式感，没增加任何能力。

## 拒绝的方案

### 每个 check 自己扫盘

被拒绝：冗余 IO + check 之间无法共享扫描结果。`DatasetSnapshot` 一次扫描让所有 check 消费，比各自扫快得多，也避免了 check A 看到的状态和 check B 不一致。

### DatasetValidator 类

被拒绝：`validate_dataset` 函数已经把所有状态装进返回值，不需要实例变量和 `self`。

### ReportSection 中间抽象层

被拒绝：YAGNI。当前只有一种 renderer（日志），`render_to_logger` 直接消费 `ValidationReport`。等真做第二个 renderer 时再提炼。

### 砍掉 INFO 级

被拒绝：语义上确实存在"知道一下，不阻断"的信息（如 snapshot.nc 为 None 导致 label_format 跳过）。砍到三级会让这类信息要么刷 WARNING（吓人），要么完全不报（隐藏）。

## 已知边界

- **无 SAMPLE 模式**：当前对所有图像全量扫描，没有采样加速。大数据集（>100K 图）时 `label_format` 可能慢。
- **阈值无配置化**：`PAIR_MISSING_ERROR_RATIO` / `PAIR_MISSING_WARN_RATIO` 是模块级常量，不支持命令行覆盖。待需求明确后加。
- **render 的 if/elif 分支**：`_render_details` 的 key 匹配链式 if/elif 在 check 数量到 8 个后应考虑 refactor 为注册表 dispatch。
- **无增量验证**：每次跑都是全量扫描，没有基于 hash 的增量跳过。
