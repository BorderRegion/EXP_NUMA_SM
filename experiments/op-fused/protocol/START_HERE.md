# 本轮入口：T10 / RTX 5070 Ti 算子内调度与合法融合

版本：2026-10-15 v1。两个平台使用同一份协议，独立执行，最后由用户搬运结果并做 CPU 合并。

**这不是旧 Green Context 调度器的移植，也不是一个新的大模型。** 本轮复用成熟 GEMM / attention 的计算主体，把新增任务选择放在算子内部，把必要元数据尽量随现有生产阶段产生。目标是判断：在同样已融合、同样使用 CUDA Graph 的强基线之外，还有没有可推广的调度增量。

## 阅读顺序
1. `CODEX_MASTER_TASK.md`：连续流程和授权。
2. `docs/01_PLATFORM_AND_SCOPE.md`：两平台真实能力、资源缺项。
3. `docs/02_OPERATOR_METHOD.md`：唯一候选与可实现的参考算法。
4. `docs/03_FUSION_AND_LAUNCH_CONTRACT.md`：必须首先落实的实现层级。
5. `docs/04_BASELINES_AND_ATTRIBUTION.md`：强基线、融合×调度对照。
6. `docs/05_WORKLOADS_AND_SPLITS.md`、`06_MEASUREMENT_AND_STATISTICS.md`、`07_CORRECTNESS.md`。
7. `docs/08_EXECUTION_LOGGING_AND_DELIVERY.md`、`09_SOURCES_AND_NOVELTY.md`。

## 两台机器的启动
在 T10 上：`platform=t10`；在 5070 Ti 上：`platform=rtx5070ti`。
只使用当前主机已有工具、源码、模型和数据。不 SSH、不远程 Git、不下载、不自动租卡或升级驱动。Codex 客户端与模型服务的正常连接不属于实验数据管线。

若缺库或模型，先读 `templates/LOCAL_PATHS.json`，只检查给定根目录和旧 RESOURCE_LOCK 指向的路径。**一次性列缺项，不反复联网请求，不以随机权重/CPU模拟冒充实际 LLM。** 有依赖的核心算子缺失时保留该分支缺项，其余分支连续执行。

## 随包 CPU 工具
```bash
python tools/check_plan.py
python -m unittest discover -s tests -v
python tools/make_matrix.py --out planned_matrix.jsonl
```
这些命令不访问 GPU 或网络。参考 packet 枚举器只验证逻辑覆盖，不是高性能 GPU scheduler；矩阵生成器只产生计划，不产生性能数据。实际 CUDA adapter、fusion hook、runner 和数据仍由 Codex 实现。

## 最终报告
`reports/OPERATOR_FUSED_SCHEDULING_REPORT_<platform>.md`

同时交付：生产 launch 清单、算子/完整层/模型分层结果、真实与合成来源、所有失败与 NA、代码/数据索引和预算。普通中间检查不暂停；完整分支完成后一次性返回。
