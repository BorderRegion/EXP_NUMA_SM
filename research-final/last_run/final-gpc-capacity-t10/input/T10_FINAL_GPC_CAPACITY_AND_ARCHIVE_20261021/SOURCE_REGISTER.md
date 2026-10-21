# 来源登记与设计边界

## 用户材料（历史事实）

- `sources/HISTORY_GPC_TOPOLOGY.md`：本机实读配置、SM→GPC/TPC映射、只读RM权限与编号语义。
- `sources/HISTORY_VECTOR_GQA.md`：第19阶段数学体、16B搬运、DIRECT/BLIND接口和强基线缺口。
- `sources/HISTORY_STATE_DIAG.md`：动态100W、提交节奏、功率限制累计计数，固定频率未执行。
- `sources/HISTORY_QUOTA_CLOSURE.md`：旧共置方案收束，不被本轮自动推翻。
- `sources/HISTORY_CPU_GPC_LINK.md`：旧地址偏好与实读GPC的CPU交叉，对物理域仍有限制。

这些原文按原样复制，未修正文中旧路径或性能。来源哈希见`source_manifest.json`；复制与哈希不代表独立复核了历史GPU结果。

## 本轮新设计

16小时计划、24小时硬上限、6小时GPU预算；容量子集、任务范围、CAP/WRONG、全部新矩阵及归档规格都是本次新设计，不是来源文件已有结果。不把设计值写进未来结果栏。

## 本次核对的第一手外部文档（2026-10-21）

1. NVIDIA System Management Interface：`-lgc`是期望锁频、需权限；SW Power Cap可降低实际频率。
   https://docs.nvidia.com/deploy/nvidia-smi/index.html
2. CUDA Driver API 13.2 Green Contexts：7.x资源粒度；分区不保证任意kernel并发/独立前进。
   https://docs.nvidia.com/cuda/archive/13.2.0/cuda-driver-api/group__CUDA__GREEN__CONTEXTS.html
3. Turing Tuning Guide：资源占用、指令/内存优化和同步约束，不能从occupancy代理直接推出利用率。
   https://docs.nvidia.com/cuda/turing-tuning-guide/index.html
4. Nsight Compute Profiling Guide：clock/cache/replay/serialization影响，profile与主计时分离。
   https://docs.nvidia.com/nsight-compute/ProfilingGuide/index.html

本地安装版本优先；Codex离线，不要求打开上述页面或安装新工具。本轮没有重新搜索整个研究领域，也不提供新颖性或可发表保证。

历史CSV从既有GPC结果包的冻结目录精确提取，仅用于CPU核对；不能代替本轮活跃绑定/读数。
