# T10 Selective Reorder Repair V2

本目录是 20261017 V2 的独立执行目录，旧 `selective-reorder-t10` 只读。当前是否完成以 `STATUS.md`、run 账本和最终报告为准。输入包里的 `DESIGN_NOT_EXECUTED` 和 `measured:false` 是未改动的原设计状态，不是本次执行状态。

## 阅读顺序

1. `reports/T10_SELECTIVE_REORDER_REPAIR_V2_REPORT.md`：结果、失败、缺项与结论边界。
2. `reports/ANALYSIS_CONTRACT.md` 和 `freeze/FREEZE_SEAL.json`：事前统计和冻结选择。
3. `runs/<run>/derived/`：可复算汇总。
4. `runs/<run>/raw/<worker>/`：原始窗口、请求、数值检查、遥测、命令、来源快照。
5. `reports/ENGINEERING_NOTES.jsonl`：工程修复和记录限制。

## 只用 CPU 复算

在解压后的目录中运行 `python3 recompute.py`。需要 Python、NumPy 和本机兼容的 x86-64 Linux CPU 动态库加载支持；不调用 Torch/CUDA，不触发 GPU 实验，不联网。脚本校验包内 SHA、原始窗口/请求均值与配对比值、24-shape 拟合与 LOSO、Python/C++ 冻结动作，再复算派生统计。它读取本目录的 run，不读取原机器上的旧绝对路径。若已编辑文件，SHA 校验会拒绝把修改后的文件冒充原包。

包内同时保留 C++ CPU 源码。若冻结的CPU动态库因另一台机器的架构/ABI不能加载，复算入口会尝试用本机g++在临时目录重建；不改原二进制和SHA清单，不联网安装。不同 NumPy/编译器可能产生细小浮点差异；复算比较使用明确容差，不改冻结规则。

## 实际执行入口

- S0：`check_legacy.py`；旧 52 shapes×5 policies×6 H 的 1560 项等价和 allocator hook。
- S1：`aa.py`，两个独立进程，各 12 个历史 episode。
- S2：`pair_suite.py CALIBRATION`、`card_v2.py`、`setup_costs.py`；`queue_first.py` 串行持有既有 GPU 锁。
- S3：`build_card.py`、`freeze_v2.py`、`generate_v2.py`、`allocation_check.py`、`build.py`、`validate_host.py`；本阶段无 GPU kernel 工作。
- S4：`queue_formal_v2.py` 按不含候选胜负的成本预测冻结完整/预定缩减范围，保留六个进程块和四个 PC 直接对照。
- S5：`deployment_v2.py`、`lifecycle_v2.py`，由 `queue_deploy_v2.py` 串行执行；所有 V 都进入三条真实序列。
- S6：`profiles.py` 只捕获预定四个 V；`analysis_v2.py`、`supplement_v2.py`、`evidence_audit_v2.py`、`figures_v2.py`、报告及打包脚本完成审计。

`src/` 中还保留继承的旧分析/资格脚本供来源审阅；带 `_v2` 的上述入口和本节明确列出的共享模块是本轮流程。不要用旧 `generate_policy.py` 重写新的 `policy.hpp`。

## 构建和成本边界

数学 `kernels.cu/.cuh`、CUTLASS adapters 及生产/诊断 cubin 均与旧轮核对。新代码只修改宿主测量、选择与计划绑定。GPU 重建仍依赖原机 CUDA/CUTLASS 环境；精简包不复制数 GB 第三方库或旧 GPU 原始数据。最后版本 cubin 只保留一份，两个宿主构建和构建日志/哈希保留。源快照归档按 worker 保存，不把旧数据改写成新结果。

所有 GPU-worker 时间按既有锁持有时间计费，旧账本 70.171806 分钟保留；本轮 cap=min(240,330−旧账本)。100 W 动态频率、风扇和过温保护保持；无非交互管理权限时不尝试口令或关闭保护。本轮没有下载、安装、SSH、付费资源或新硬件。

## 研究限制

这是一块 T10 上的合成 GEMM/FFN 与宿主请求序列，不是完整预训练 LLM。资源卡/PC 位置效果不自动代表物理 NUMA。1 Hz 遥测不能证明每个微秒窗口频率相同。固定 Plan 省去每请求选择，但计时仍使用图事件/输出边界；Graph 不等于数学融合。FFN 第二 GEMM 固定共用 LIB。H=1024/4096 的生命周期点明确为由 64 个实测稳态请求推算的 ESTIMATED。
