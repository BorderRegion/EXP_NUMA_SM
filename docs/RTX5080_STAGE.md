# 2026-10-13：RTX 5080 上的四轮尝试

这是 T10 主线开始前一天，在另一台机器（桌面机，RTX 5080）上做的四轮尝试。它们**不计入** 28 个 T10 阶段，也不与 T10 的数字合并：设备不同、计时代码不同、独立单位不同，合在一起算会得到没有意义的平均数。

四轮都在一天内结束，结论都是负的或未建立的：

| 轮次 | 做了什么 | 结论 | 报告 |
|---|---|---|---|
| R1 | 资源盘点、预注册、CPU 分析工具与合成数据自检 | `BLOCKED_LOCAL_RESOURCE`：本地缺 CUDA 工具链、测量 runner、renderer 与资产，硬件测量 0 次 | [AFFINITY_RENDER_OPPORTUNITY_REPORT.md](rtx5080/AFFINITY_RENDER_OPPORTUNITY_REPORT.md) |
| R2 | 离线恢复工具链与 Graphdeco 渲染器，做按资源复用的调度原型 | `NO_INCREMENTAL_OPPORTUNITY_ON_5080`：36 个 session、18,432 帧；候选比原生慢 42.4%，比只做负载均衡的基线慢 26.9%，0 处输出不匹配 | [RTX5080_RENDER_SCHEDULING_RESUMED_REPORT.md](rtx5080/RTX5080_RENDER_SCHEDULING_RESUMED_REPORT.md) |
| R3 | 84 个 SM × 地址区域的静态采样；K=2 分组，两次新分配留出 | `NO_ACTIONABLE_AFFINITY_IN_TESTED_SCOPE`：留出预测 0.331%（区间 0.253–0.382%），低于冻结的 3% 门槛 | [STATIC_AFFINITY_SPECIALIZATION_REPORT.md](rtx5080/STATIC_AFFINITY_SPECIALIZATION_REPORT.md) |
| R4 | 把 R3 的图装进 40/40/4 的 Green 执行器，与 Native、置换聚合、盲选完整配对 | `NO_DEPLOYABLE_GAIN_ON_TESTED_GROUPS`：192 MiB 普通负载慢 1.388%（每 epoch 多 14.941 µs），`.cg` 慢 1.455%，均 6/6 为负 | [STATIC_AFFINITY_CAUSAL_COMPLETION.md](rtx5080/STATIC_AFFINITY_CAUSAL_COMPLETION.md) |

## 一、机器与边界

- 设备：NVIDIA GeForce RTX 5080，计算能力 12.0，84 个 SM，报告 64 MiB L2。GPU 同时承担桌面显示，不是独占设备。
- 软件：Ubuntu 26.04，驱动 595.99.02，工作区 CUDA 编译器 13.2.51，driver/runtime API 13020。
- 没有修改驱动、功耗、频率、超时或系统权限；没有付费资源。
- 这台机器**没有**参与 T10 的 28 个阶段。T10 的结论不能外推到 5080，5080 的结论也不能外推到 T10。

## 二、四轮之间怎么接

1. **R1 没测到硬件。** 只有只读的 CUDA 初始化成功，`nvcc`、`ptxas`、`ncu`、`nsys` 都不在；没有可修改的 renderer，也没有模型和相机数据。因此 R1 只交了资源缺口清单、预注册和 CPU 分析工具，没有把“资源不足”写成“硬件没有机会”。
2. **R2 先补资源，再测调度。** 离线工具链、Graphdeco `diff-gaussian-rasterization` 与 Train/Bonsai 资产就位后，先跑 pilot，遇到一次 Xid 13/43；修复队列的同步问题后，按预注册走阴性分支，只做 36 个 session 的确认，不扩展到 180 个 session 的完整矩阵。
3. **R3 换了一个更小的问题。** 不再问“渲染调度有没有用”，而是问“同一个地址区域在不同 SM 上的耗时有没有可重复的差异”。有：留出预测是弱的正数，但过不了 3% 的可行动门槛，于是按预注册停在报告分支，没有把地图接到渲染器。
4. **R4 补的是因果缺口。** R3 只做了“预测”，没有“执行同一个图”。把图实际装进 Green 分组并跑满 144 个正式 session 后，192 MiB 的普通负载比 Native 慢，而不是快。小工作集里仍有零散的正数（普通负载 A 比几何置换聚合快 4.644%，`.cg` 的 A 比盲选 I 快 2.034%），但没有同时胜过全部三个参考。R4 还有一个已披露的协议偏差：四个 PRESSURE 种子与资格阶段重叠。

## 三、代码、数据与文件说明

2026-10-21 已补充原始实验材料：

| 轮次 | Git 证据目录 |
|---|---|
| R1 | [资源盘点与 CPU 准备](../experiments/rtx5080-20261013/render-opportunity/) |
| R2 | [渲染调度与最终报告](../experiments/rtx5080-20261013/render-scheduling/)（早期 V2 单独保留） |
| R3 | [静态 SM × 地址亲和采样](../experiments/rtx5080-20261013/static-affinity/) |
| R4 | [Green 执行器与因果配对](../experiments/rtx5080-20261013/static-affinity-causal/) |
| 本机补充 | [原包未覆盖的代码、日志与小记录](../experiments/rtx5080-20261013/local-supplement/) |

- 五个交付原包和补充原始输出归档在 [5080 Release](https://github.com/BorderRegion/EXP_NUMA_SM/releases/tag/records-2026-10-13)。补充包包括此前未上传的 R2 渲染原始输出，分为四片。
- 下载、逐文件校验和恢复说明见 [归档入口](../archive/rtx5080/README.md)，机器可读清单见 [INDEX.json](../archive/rtx5080/INDEX.json)。Git 中的证据副本保留原始字节；大型数据和部分构建二进制从 Release 获取。
- `docs/rtx5080/` 的四份报告与原配图继续保留。该目录的历史相对数据链接仍对应原工作目录；沿上表进入对应实验目录即可查看原布局中的代码和小型记录，大型文件按归档说明恢复。
- 外部 CUDA 工具链、场景资产和绘图库没有打包；依赖来源与版本记录保留。详见归档入口的保存范围。
- 本次仅补传已有记录，没有更改原结论，没有重跑 GPU，也没有将四轮计入 T10 的 28 个阶段。

## 四、不能从这里推出什么

- 不能推出“RTX 5080 上没有 NUMA 或 SM 差异”。R3 测到了弱的正数，R4 只说明**这套配方与预算下**没有可部署的净收益。
- 不能推出“所有渲染调度都无效”。R2 只测了一个 renderer、一种 CPU 辅助的复用原型；容量模型没有校准。
- 不能推出“地址调度一定有害”。R4 的负数是与 Native 和置换基线的配对比较，只覆盖 16 MiB 和 192 MiB 两种访问集。
- 不能把四轮的百分比相加，也不能用它们去解释 T10 的任何数字。
