# 术语表与固定数字（先读这一页）

本页是包内唯一的术语与数字来源。若其他文件与本页冲突，以 `campaign.json` 为准，并修改其他文件。

## 1. 平台标签
- `t10`：Tesla T10 16GB，目标 cc 7.5（Turing）。SM 数、GPC 数、裁剪方式均未知，必须由 CUDA 查询得到。
- `rtx5070ti`：NVIDIA GeForce RTX 5070 Ti，目标 cc 12.0（GB203）。公开规格为 6 GPC、35 TPC、70 SM、48 MiB L2、16 GB。这些是规格值，不是实测值。

## 2. 硬件与 API 术语
- SM（streaming multiprocessor）：GPU 的计算单元。
- TPC、GPC：SM 的上层分组。GPC 是图形处理簇。
- floorsweeping：厂商在出厂时屏蔽部分 SM/TPC/GPC。屏蔽后的 SM 数量是事实，但"少了多少 SM"不等于"性能损失多少"。
- Thread Block Cluster（cc 9.0 及以上）：同一 cluster 内的 block 会被放在同一 GPC 内。因此"cluster 内 SM 共现"可以证明同 GPC，但"没有共现"不能证明不同 GPC。`k=1` 的普通 launch 不能作为同 GPC 证据。
- Green Context：CUDA 提供的"SM 分组"接口。分组是不透明的选择，不能任意指定逻辑 SM 列表，也不保证并发前进。
- `%smid`：block 执行时所在的 SM 编号。只表示读取瞬间的位置，不保证连续，也不保证跨调度稳定。
- Xid、TDR：GPU 健康事件（设备错误、驱动超时恢复）。出现即停止 GPU 分支，见 §5。

## 3. 平台与阶段代码
- 阶段 E0–E6：E0 本地资源盘点与可运行基线；E1 拓扑与可控资源；E2 容量与并发；E3 唯一候选与强基线；E4 主应用；E5 留出、生命周期、共置（条件式）；E6 平台收束与合并。
- 策略代码（每个策略是一种任务分配方式）：
  - `N`：Native，原生优化执行，必需参考。
  - `I`：同执行器下，按 SM 数量等分逻辑任务（拓扑盲）。
  - `S`：同执行器下，固定空间顺序（Morton 或 tile 顺序）加 SM 比例分配。
  - `L`：使用开发任务权重，但把每个 SM 视为相同服务能力。
  - `R`：每组单一速率的加权分配，是必需的强简单基线。
  - `T`：按 SM/GPC/cluster 可用数量的简单拓扑启发式；证据不足时为 NA。
  - `M`：本方法（类型化、并发校准的静态 minimax 候选）。全部实验中只有一个 M。
  - `P`：M 的预先固定置换版本，资源份额与任务集合不变。
- 微核家族：
  - `K0 UINT_COMPUTE`：计算密集的整数递推。
  - `K1 RESOURCE_SENSITIVE`：依赖寄存器或共享内存资源的 kernel。
  - `K2 CACHE_REUSE`：数据被多次复用的 kernel。
  - `K3 STREAMING`：流式读写，关注字节吞吐。
- 布局代码 `G0`–`G3`：G0 单组（全部可用 SM）；G1 约一半加余数组；G2 约 1/3 与 2/3；G3 本机明确支持的另一种组内模式，不支持则为 NA。
- 工作负载：
  - `W1`：本地现成 CUDA 3DGS rasterizer（Graphdeco 版本，锁定 commit）。
  - `W2`：独立稀疏行算子（CSR 行 gather）。没有真实来源时只能作为 `SYNTHETIC` 机制对照，不算真实应用。

## 4. 固定数字（与 campaign.json 一致）
| 项目 | 数字 | 说明 |
|---|---|---|
| 每平台 GPU worker | 1 | 同一时刻只运行一个 GPU 任务 |
| CPU 编译并行上限 | 4 | `min(4, 可用 CPU 核数的一半)` |
| 微测试显存上限 | 512 MiB | 每个微测试 |
| 真实应用显存余量 | max(2 GiB, 15% 实际总显存) | 始终保留 |
| 微测试预热 / 测量 | 32 / 128 个 epoch | 每个 epoch 不是独立重复 |
| 应用预热 | 至少 128 帧且至少 1 秒 | 取较长者 |
| 应用测量 | 512 帧 | 每个 session |
| 正式进程块 | 6 | 每个 cell 6 个独立进程块 |
| 公共布局上限 | 4 | 每台机器 |
| 新候选数 | 1 | |
| 编译期特化实例上限 | 4 | 只在表方案有效后才做 |
| 微核探针目标 | < 2 ms | 超过 20 ms 上限要减小规模 |

随机种子：`selection` 2026101401，`process_order` 2026101402，`bootstrap` 2026101403，`task_inputs` 2026101404。

## 5. Session 上限（sessions 或 launches，不是小时）
| 集合 | 上限 |
|---|---:|
| E1 普通覆盖 | 216 launches |
| E1 cluster（仅支持平台） | 432 launches |
| E2 公共容量 | 144 sessions |
| E2 cluster 机制（仅 rtx5070ti） | 96 sessions |
| E3 部署机制 | 252 sessions |
| E4 主应用 | 432 sessions |
| E4 替代确认 | 144 sessions |
| E5 留出 | 36 sessions |
| E5 分辨率/规模 | 18 sessions |
| E5 共置 | 72 sessions |
| E5 生命周期/常量 | 27 sessions |
| E5 记录扰动 | 12 sessions |

上限不是 KPI。能力缺失写 `NA`，资源缺失写 `BLOCKED`，未运行的格子不填 0。

## 6. 成本记录（不设时长上限）
- 不设 GPU 小时上限，也不预先分配小时预算。
- 每个 run 记录：`worker_seconds`（GPU worker 实际占用秒数）、`actual_cost`（实际费用）、`cost_unit`（费用单位）。
- 费用单价未知时填 `null`。不能因为"没有新增采购"就把实际费用记为 0。
- 一次性资源和初始化的真实占用，即使实例空闲仍在计费，也要记录。

## 7. 结果状态
- Run 状态：`PLANNED`（已计划）、`SUCCESS`、`FAILED`、`ABORTED`（进程中断，末记录缺失）、`NOT_RUN`、`UNSUPPORTED`。
- 最终研究结论（六选一，见 `docs/05` §7）：`PAPER_OPPORTUNITY_WITH_GAPS`、`ENGINEERING_GAIN_ONLY`、`TOPOLOGY_OBSERVED_NO_DEPLOYABLE_GAIN`、`NO_MATERIAL_CAPACITY_ASYMMETRY_IN_SCOPE`、`CONTROL_OR_RESOURCE_LIMITED`、`SAFETY_STOP_WITH_PARTIAL_EVIDENCE`。

## 8. 停止规则
- 只有以下情况暂停全部 GPU 工作：设备丢失、Xid/TDR 或系统恢复；需要新增付费、联网、升级驱动或权限；必须修改正确性合同或采样算法；核心 runner 无法可信运行。
- 普通编译错误、资源查询返回 unsupported、单个候选数值失败，都不停止全部工作。只隔离失败的候选或条件，其他合法工作继续。
- 所有暂停和隔离都要写入 `STATUS.md`。

## 9. 不再使用的旧设计名
`V3`、`SER compiler`、证据检查器、每帧 CPU bundle planner、`旧Q` 的 atomic claim、`RTX 5080` 旧结果：均已停用。这些名字只允许出现在背景说明中，不能作为本轮的方法、基线或实验条件。
