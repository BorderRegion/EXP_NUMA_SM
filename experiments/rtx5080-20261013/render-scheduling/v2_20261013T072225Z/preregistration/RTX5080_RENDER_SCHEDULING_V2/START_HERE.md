# RTX 5080 渲染重调度研究：本机连续实验 v2

设计日期：2026-10-13。此包替代 `AFFINITY_RENDER_OPPORTUNITY_20261011` 的后续执行指令；旧代码、计划和结果不删除、不改写。不是 4060 计划的型号替换。

## 一句话任务

在当前本机 RTX 5080 上，研究**任务资源复用、有效缓存工作集与不均匀负载的联合调度**；有限测量真实位置亲和性，仅在信号与控制能力均成立时加入拓扑项。**没有证实 NUMA，不阻塞已经授权的缓存／负载路线，也不能把该路线冒充 NUMA。**

## 阅读顺序

1. `CODEX_MASTER_TASK.md`：完整授权、连续流程及终点。
2. `HARDWARE_5080_AND_BRANCHES.md`：5080 特有前提与路线判定。
3. `METHOD_AND_BASELINES.md`：一个方法、强基线和机制消融。
4. `CORRECTNESS_AND_RUNTIME.md`：合法任务边界与执行器要求。
5. `EXPERIMENTS_AND_STATISTICS.md`：校准、留出、计时、分母与预算。
6. `OFFLINE_RESOURCES_AND_LOGGING.md`、`RELATED_WORK_AND_SCOPE.md`。
7. `campaign.json`：机器可读预算和计划上限。

只读检查计划：

```sh
python tools/plan.py check campaign.json
python tools/plan.py summary campaign.json
python -m unittest discover -s tests -v
```

以上只检查 CPU 辅助代码与计划，不访问网络、不运行 GPU、不代表 GPU 实验已实现。
`templates/device_inventory.cu` 是可选的本机只读设备查询源码；需要本地 nvcc 编译，由 Codex 在获授权实验主机上运行。提供者未在 RTX 5080 上编译或执行它。

## 本次交付终点

`reports/RTX5080_RENDER_SCHEDULING_REPORT.md` 与 `reports/CONTRIBUTION_CARD.md`。
正常情况下连续完成 E0–E6，途中自动处理既定分支，最后一次性交付。GPU 安全、修改正确性合同、增加付费和系统权限变更是例外。

## 这次没有授权

不恢复 V3、AutoSER、state shaping、证据检查器或 GRAPH_MEMORY；不训练模型；不迁移完整 Vulkan renderer；不下载或联网；不修改驱动、TDR、MIG、MPS、全局时钟／功耗；不擅自停止其他作业；不增加第二个候选算法救结果。

## 必须保留的区别

- 5080 ≠ B200；旧 4060 的性能、黄金图像、编译产物不作为新卡基线。
- 逻辑任务组 ≠ 物理 NUMA 域；block 顺序 ≠ SM 固定位置。
- 原生 renderer 加速 ≠ 新方法优于强基线；同一 renderer 的三个场景 ≠ 三个独立程序。
- 统计显著 ≠ 论文成立；阴性拓扑结果 ≠ 所有调度没有空间。
- 本包中的参数、预算和算法是研究设计，不是已测数据。
