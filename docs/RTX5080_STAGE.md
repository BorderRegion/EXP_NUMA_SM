# 2026-10-13：RTX 5080 上的四轮尝试

这是 T10 主线开始前一天，在 RTX 5080 桌面主机 `ws-X870-AORUS-ELITE-WIFI7-ICE` 上做的四轮尝试。2026-10-21 已核对历史环境记录与当前主机，确认这是当前这台桌面机；此前的“另一台机器”是相对于 T10 实验主机而言。它们**不计入** 28 个 T10 阶段，也不与 T10 的数字合并：设备不同、计时代码不同、独立单位不同，合在一起算会得到没有意义的平均数。

四轮都在一天内结束，结论都是负的或未建立的：

| 轮次 | 做了什么 | 结论 | 报告 |
|---|---|---|---|
| R1 | 资源盘点、预注册、CPU 分析工具与合成数据自检 | `BLOCKED_LOCAL_RESOURCE`：本地缺 CUDA 工具链、测量 runner、renderer 与资产，硬件测量 0 次 | [AFFINITY_RENDER_OPPORTUNITY_REPORT.md](rtx5080/AFFINITY_RENDER_OPPORTUNITY_REPORT.md) |
| R2 | 离线恢复工具链与 Graphdeco 渲染器，做按资源复用的调度原型 | `NO_INCREMENTAL_OPPORTUNITY_ON_5080`：36 个 session、18,432 帧；候选比原生慢 42.4%，比只做负载均衡的基线慢 26.9%，0 处输出不匹配 | [RTX5080_RENDER_SCHEDULING_RESUMED_REPORT.md](rtx5080/RTX5080_RENDER_SCHEDULING_RESUMED_REPORT.md) |
| R3 | 84 个 SM × 地址区域的静态采样；K=2 分组，两次新分配留出 | `NO_ACTIONABLE_AFFINITY_IN_TESTED_SCOPE`：留出预测 0.331%（区间 0.253–0.382%），低于冻结的 3% 门槛 | [STATIC_AFFINITY_SPECIALIZATION_REPORT.md](rtx5080/STATIC_AFFINITY_SPECIALIZATION_REPORT.md) |
| R4 | 在实际 40/40/4 Green 分组上重新校准地图，与 Native、置换聚合、盲选完整配对 | `NO_DEPLOYABLE_GAIN_ON_TESTED_GROUPS`：192 MiB 普通负载慢 1.388%（每 epoch 多 14.941 µs），`.cg` 慢 1.455%，均 6/6 为负 | [STATIC_AFFINITY_CAUSAL_COMPLETION.md](rtx5080/STATIC_AFFINITY_CAUSAL_COMPLETION.md) |

## 一、机器与边界

### 主机归属核验（2026-10-21）

| 标识 | 2026-10-13 的历史记录 | 当前主机只读查询 |
|---|---|---|
| 主机名 | `ws-X870-AORUS-ELITE-WIFI7-ICE` | 相同 |
| GPU UUID | `GPU-b864b6c3-6dad-2596-5e83-3b15d32a13b5` | 相同 |
| GPU / PCI 地址 | RTX 5080 / `0000:01:00.0` | 相同 |
| 驱动 | `595.99.02` | 相同 |
| 系统 / 内核 | Ubuntu 26.04 / `7.0.0-38-generic` | 相同 |

核对来源为本机 `/home/ws/文档/ChatGPT/EXP_NUMA/`：R1 的 `results/raw/affinity_20261013T064931Z_b2cdc88d/environment_host.json`、R2 的环境和硬件记录，以及 R3/R4 的 `results/raw/*/hardware_before.csv` 等硬件记录。筛查到包含 GPU UUID 的记录分别为 2、81、23、41 份，均只有上述同一 UUID。该数量是来源记录数，不是独立实验样本数。

仓库四份报告也逐一与本机原件比对：R1、R3 字节相同；R2、R4 仅图片链接路径不同，其余正文相同。这次核验确认机器归属与报告副本的一致性，没有重跑 GPU 或重新验证全部统计结论。原始日志留在本机，仓库继续只保存报告与配图。

### 实验时的环境与解释边界

- 设备：NVIDIA GeForce RTX 5080，计算能力 12.0，84 个 SM，报告 64 MiB L2。GPU 同时承担桌面显示，不是独占设备。
- 软件：Ubuntu 26.04，驱动 595.99.02，工作区 CUDA 编译器 13.2.51，driver/runtime API 13020。
- 没有修改驱动、功耗、频率、超时或系统权限；没有付费资源。
- 这台机器**没有**参与 T10 的 28 个阶段。T10 的结论不能外推到 5080，5080 的结论也不能外推到 T10。

## 二、四轮之间怎么接

1. **R1 没测到硬件。** 只有只读的 CUDA 初始化成功，`nvcc`、`ptxas`、`ncu`、`nsys` 都不在；没有可修改的 renderer，也没有模型和相机数据。因此 R1 只交了资源缺口清单、预注册和 CPU 分析工具，没有把“资源不足”写成“硬件没有机会”。
2. **R2 先补资源，再测调度。** 离线工具链、Graphdeco `diff-gaussian-rasterization` 与 Train/Bonsai 资产就位后，先跑 pilot，遇到一次 Xid 13/43；修复队列的同步问题后，按预注册走阴性分支，只做 36 个 session 的确认，不扩展到 180 个 session 的完整矩阵。
3. **R3 换了一个更小的问题。** 不再问“渲染调度有没有用”，而是问“同一个地址区域在不同 SM 上的耗时有没有可重复的差异”。有：留出预测是弱的正数，但过不了 3% 的可行动门槛，于是按预注册停在报告分支，没有把地图接到渲染器。
4. **R4 补的是执行比较的缺口。** R3 的 42/41 学习分组不能直接当作实际 40/40/4 Green 分组。R4 在每个新进程的实际 Green 分组上重新校准并生成地图，再与盲选、置换和 Native 完整配对，共跑满 144 个正式 session。原报告明确说明没有使用 R3 的旧学习分组。因此，R4 不能描述为“直接部署 R3 的同一张地图”。R4 中，192 MiB 的普通负载比 Native 慢，而不是快。小工作集里仍有零散的正数（普通负载 A 比几何置换聚合快 4.644%，`.cg` 的 A 比盲选 I 快 2.034%），但没有同时胜过全部三个参考。R4 还有一个已披露的协议偏差：四个 PRESSURE 种子与资格阶段重叠。

## 三、文件说明

- `rtx5080/` 下是四份报告原文，正文未改动。只把图片链接改成了仓库内路径：R2 的三张图原来写的是本机绝对路径，R4 的四张图原来写的是 `reports/figures/`；现在统一指向 `rtx5080/figures/`。
- 报告正文里的其他相对链接（例如 `../results/...`）指向原始工作目录，本仓库**没有**这些文件，点开会是空链接。
- 原始数据、源码、冻结件和 664 MB 的归档包都**不在**本仓库；需要完整证据时用本机原始项目。这里保存的只是报告与结论。

## 四、不能从这里推出什么

- 不能推出“RTX 5080 上没有 NUMA 或 SM 差异”。R3 测到了弱的正数，R4 只说明**这套配方与预算下**没有可部署的净收益。
- 不能推出“所有渲染调度都无效”。R2 只测了一个 renderer、一种 CPU 辅助的复用原型；容量模型没有校准。
- 不能推出“地址调度一定有害”。R4 的负数是与 Native 和置换基线的配对比较，只覆盖 16 MiB 和 192 MiB 两种访问集。
- 不能把四轮的百分比相加，也不能用它们去解释 T10 的任何数字。
