# ADR-005: runtime_config 子系统 — Pydantic + 三源合并 + 链表溯源架构

## 上下文

D4 (`data_validation`) 解决了"这数据能不能训"的问题。D5 要回答"怎么训"——训练有 60+ 参数（epochs / batch / lr0 / optimizer / cos_lr / mosaic / mixup / hsv_h / box loss 权重...），每个都有默认值，也都有可能需要调。

朴素方案（argparse + 一个 default YAML）在工业场景下会暴露 4 个伤痛：
1. 字段散落在 argparse `add_argument`、YAML 默认值、`vars(args)` 过滤三处
2. 无验证——`imgsz=649`（非 32 倍数）、`batch=0`（零批）、`device="cpuu"`（拼错）全部静默通过
3. 无溯源——跑完只知道 `lr0=0.001`，不知道是 CLI/YAML/默认值
4. 配置即文档不成立——用户拿到 `mosaic: 1.0`，不知道范围、默认值、何时调

`runtime_config` 子系统用 Pydantic + 字段级元数据 + 三源合并器 + 配置生成器一次性解决这四个问题。

## 八大决策

### 1. Pydantic BaseModel + extra="forbid"

用 Pydantic 替代 argparse 做配置字段定义和验证。`ConfigDict(extra="forbid")` 拒绝拼错的字段名，在 YAML/CLI 进配置的入口就拦截。字段级 ge/le/gt/lt 约束 + `field_validator` + `model_validator` 覆盖单字段和跨字段验证。

### 2. 字段元数据 5 槽位

每个 Pydantic Field 通过 `json_schema_extra` 携带 5 个槽位：`group`（分组）、`examples`（示例值）、`tips`（中文使用建议）、`yaml_comment`（YAML 模板注释）、`sensitive`（敏感字段标记）。所有元数据是字段定义的唯一真相来源——ConfigGenerator 反射这些元数据生成 YAML 模板前导注释。

### 3. task（SSoT 语义）+ experiment_name（实验标识）正交拆分

legacy 的 `task` 字段承担双重职责：既是语义（detect/segment），又嵌入实验名（如 `detect_val` 做目录名）。D5 拆成两个字段：
- `task`：SSoT 封闭取值，由 `Task.all()` validator 硬墙拒绝非法值
- `experiment_name`：自由的实验标识，None 时由 ultralytics 自动生成

train 的 `task` 传给 ultralytics；val/infer 的 `task` 不进 `to_ultralytics_kwargs()`（从权重/模型推断）。

### 4. 三源合并 + 链表式溯源

优先级 CLI > YAML > DEFAULT。每一层覆盖都记录 `ConfigMetadata`（链表节点），`overridden_from` 指向上一个版本。`chain()` 遍历完整覆盖链，`chain_str()` 格式化为 `"300(CLI) ← 200(YAML) ← 100(DEFAULT)"`。额外源（ENV、etcd、k8s）通过字符串 source_id 扩展，不扩 enum。

三个产物：
- `get_source_report()` — 给人看的分组报告
- `get_conflict_report()` — 被覆盖字段清单
- `to_audit_log()` — 给 ELK/数据库的结构化审计（只含来源信息，不含字段值）

### 5. Loader 只加载不验证不合并不自动生成

`YAMLLoader` / `CLILoader` 各负责把外部数据装进 dict，不做字段验证（Pydantic 的活），不做合并（Merger 的活），文件不存在时不自动生成模板（显式命令触发，不隐式自动）。fail-fast + 修复指引：报错信息包含 `odp-gen-config <name>` 命令。

### 6. ConfigGenerator 反射生成 YAML 模板

不从生成器里维护第二份字段表。`ConfigGenerator._generate_yaml()` 调用 `config.get_field_groups()` / `config.get_field_metadata()` 反射 Pydantic 模型元数据，组装三段注释（yaml_comment / 示例 / tips）+ 尾部 FAQ。双闸门保护用户编辑过的模板：`overwrite=False` 默认不覆盖，`overwrite=True` 时自动备份原文件。

### 7. CLI entry-point 直绑 generator，不走 cli/ 薄包装

`odp-gen-config = "odp_platform.runtime_config.generator:main"` 直绑到 generator 模块。generator 既是反射工具（API），又是 CLI 主流程——不需要立 `cli/generate_config.py` 薄包装。同时保留 `python -m odp_platform.runtime_config.generator <name>` 作为装包前备胎。

### 8. `__init__.py` 作为对外合同

子系统对外暴露 14 个公开符号（4 配置类 + 3 加载器 + 3 合并器 + 1 生成器 + 3 个 build_* 便捷函数）。`__all__` 是唯一真相——不在 `__all__` 里的内部细节 (`_drop_none` 等) 调用者自负风险。三个 `build_*` 函数各自返回不同类型的 config（不是通过 mode 参数分发），避免 Union 返回类型让 mypy 无法推断。

## 拒绝的方案

### 纯 argparse + YAML 朴素方案

被拒绝：字段三处定义（argparse 一次、YAML 一次、vars(args) 过滤一次），无验证，无溯源。这个方案在 D5 阶段 1 里专门写了一版作为反面案例。

### 自动生成默认模板（文件不存在时静默生成）

被拒绝：两个真实失败场景——（1）CI 跑 5 小时，跑的是新生成的默认值，没信号反映配置不该是默认值；（2）用户拼错文件名（`train.yaml` vs `train_.yaml`），精心调参的文件没被读到。

### 立 cli/generate_config.py 薄包装

被拒绝：generator 本身既是反射工具又是 CLI，再加薄包装多一层维护成本。D2-D4 的 CLI 都在 cli/ 下是因为它们只作为 CLI 存在。

### 把 task/experiment_name 抽到 BaseConfig

被拒绝：三个子类的 task 行为不同（train 传给 ultralytics；val/infer 不传）；元数据不同（train 推荐命名 `<model>_<dataset>_<key_param>`，val 推荐 `val_<model_version>`）；推理未来可能不需要 task。语义不同的字段看起来代码重复，但抽到一起反而引入耦合。

### build_*(mode="train") 单函数通过 mode 分发

被拒绝：返回类型会变成 `Union[YOLOTrainConfig, YOLOValConfig, YOLOInferConfig]`，service 层拿到后需要 `isinstance` 判断才能让 mypy 通过。三个函数，各自类型清晰。
