# 28 个T10阶段索引

这里按时间顺序列出全部 28 个T10阶段，每个阶段一行：做了什么、得到什么、还有什么限制。

**阅读须知**

- 阶段数不是独立样本数。一个阶段里可能有开发、资格、失败、正式和补充运行。
- 表中“时间比”小于 1 表示更快；“时间减少”为正表示更快。吞吐、速度比、日志交互数不能直接互相换算。
- 原始文件的完整清单在 [archive/INDEX.json](../archive/INDEX.json)，包括没有写进本文的失败和负结果。

| 阶段 | 日期 | 做了什么 | 得到什么 | 限制 |
|---|---|---|---|---|
| 01 | 10-14/15 | 检查公开的 SM 资源分组，在 3DGS 渲染和真实图的 CSR 上对比原生实现 | 没有可部署的提速；原生实现更快 | 没有在 5070 Ti 上测；E5 未触发 |
| 02 | 10-15 | 补充对照：加入原生基线的首尾锚、顺序轮换、经验匹配 | 内部匹配有条件效应，但相对原生仍慢 | 内部匹配不等于部署收益 |
| 03 | 10-15 | 搭建算子内调度的测试框架，对比原生基线 | 156 个用例、936 个用例块、4248 个阶段；候选覆盖为 0，也就是没有实际的候选实现进入测量 | 当时缺可修改的主体；温控切换到 125/100 W，不是固定功耗 |
| 04 | 10-15 | 定好接入合同，把功耗上限固定在 100 W | 合同和源码冻结完成；100 W 上限生效 | 本阶段没有新的 GPU 测量 |
| 05 | 10-15/16 | CUTLASS 分组调度加融合 | 同一代码内比强简单策略快；但完整核仍比库慢约 2.03 倍，完整层约 1.83 倍 | 收益不能归因于新增的自适应信息 |
| 06 | 10-16 | 同 q 归因：检查数学主体的差距 | 去掉少量普通开销后，主体仍比成熟库慢约 37% | 残余差距主要在数学主体 |
| 07 | 10-16 | 逐 SM 地址探针，发现小工作集里的局部差异 | 2 SM 细分后，局部差异可以重复测到 | 9 个消费者条件没有可靠的部署证据；探针图不能直接当应用地图 |
| 08 | 10-16 | 冻结 0x33 规则，分析低并发和高并发 | 低并发时约快 0.94%–1.01%；高并发约 0.02%，区间跨零 | 高并发未证实；完整请求的净收益未建立 |
| 09 | 10-16/17 | 真实的生产者–消费者切分归并（split-K），在 LLM 形状上测试 | 相对 cuBLAS 的延迟节省为 −26.42%，即更慢；相对简单 G 方案没有额外收益 | Attention 的适配器缺失 |
| 10 | 10-17 | 选择性重排：允许回退到原生实现 | 所有正式形状都选了库实现 | 事后的理想选择有空间，但资源信息没有带来增量 |
| 11 | 10-17 | 修复选择器，并做 A/A 审计 | 102/168 组 A/A 偏移超过 5%，稳定性没有修好 | 资源版本和形状版本在新输入上没有动作差异 |
| 12 | 10-17 | 起始瞬态与 F4 退化诊断 | 同一计算反复出现 460–1010 μs 的跳变；跳变不只出现在开始 | 1% 分辨率未恢复；硬件根因没有闭合 |
| 13 | 10-17 | 运行状态与可逆的提交节奏 | 100 μs 请求间隔：主实验完成率 +20.67%，辅助复验 −5.95% | 单请求变短不等于吞吐提高；不能只引用主实验 |
| 14 | 10-17 | 统一准备流程下的节奏复验 | 四块都没有净收益：1 Hz 组 −10.53%，20 Hz 组 −7.89% | 等待成本大于处理节省；不给稳定提速结论 |
| 15 | 10-17 | 逐 SM 通信矩阵，加地址调度原型 | 通信时间比固定、随机、盲配对分别少 2.458%、1.101%、0.478% | 只是通信原型，不是 GEMM 或 LLM 的提速 |
| 16 | 10-17 | 把地址感知的归并接到真实 GEMM | 相对同核固定配对减少 0.18%，但相对原 CUTLASS 慢 1.94% | 计入完整 kernel 后没有净收益；CPU 建表不算 GPU 提速 |
| 17 | 10-17 | 页内队列、融合和更强的 GEMM 配方 | 地址队列比普通 GEMM 慢 1.28%；普通 D13 配方比 cuBLAS 快 8.616% | 收益来自普通配方选择 |
| 18 | 10-17 | GQA 解码快核和 KV 写入融合 | 六种形状相对预选库快 33.6%–55.3%；地址偏好比无偏好慢 0.96% | 收益来自共享 KV、序列切分和融合；不是整模型结果 |
| 19 | 10-18 | 类 NUMA 调度加向量化快路径 | KV 写入加注意力快 25.2%–37.8%；地址偏好比无偏好慢 1.58% | 16 字节搬运和普通任务分配有效；NUMA 本身没有额外收益 |
| 20 | 10-18 | Softmax 的 SM 配对，在冻结快核上 | 热输入相对固定配对快 2.16%；连续 32 次节奏下慢 1.48% | 条件性的效果，不能推广成通用的地址调度 |
| 21 | 10-18 | 均衡工作与固定归并者的对照 | 16 项地址对照没有过门槛；新完整核比旧快核慢 2.8%–4.3% | 工作不均、归并者、编译入口和运行节奏混在一起，不能当作裸 SM 距离 |
| 22 | 10-18 | 直接读取真实 GPC/TPC 的屏蔽分布 | GPC 0–5 启用的 SM 为 10、12、12、10、0、12 | 确定了资源分布，但不确定平面几何距离；只读查询，不是性能实验 |
| 23 | 10-18 | 按真实的同 TPC、同 GPC、跨 GPC 分组比较 | 孤立往返时间差约 1160.6、1178.9、1174.3 ns；热输入净快 0.42% | 仍输给冻结随机、错误地址和混合地址；没有稳定的 GPC 域 |
| 24 | 10-18 | 完整通信尾部代理，加地址放置 | 联合方案净 −0.36%；静态规则 BLIND54 快 0.68%（6/6 为正） | 代理排序预测能力弱；fresh 的小正值由单进程长尾拉起 |
| 25 | 10-18 | 新的固定基线，加低成本的真实核采样 | BASE54 复验快 0.83%（热）和 0.33%（重写）；采样方案净 −0.27% 和 −0.26% | 扣费前也没有正收益；保留 BASE54，不再继续同类 Softmax 搜索 |


| 26 | 10-19 | GPC竞争与GQA共置 | 微基准分散有局部收益，完整10/46共置仍慢于强基线 | 不能把竞争效应当物理NUMA或部署收益 |
| 27 | 10-19 | 资源份额和尾部释放 | LONG比同份额固定快24.972%；对强串行+0.633%且区间跨零 | PACK局部收益不在确认后改选；RAGGED串行alias |
| 28 | 10-21 | 同GPC容量与完整worker分工，最终归档 | 四锚CAP配对ready慢约2.0%–19.6%；48有限容量条件完成 | 三档状态资格失败，完整固定状态矩阵NA，非硬件不可能证明 |

最新稳定stage_uid、每阶段复核级别、claim证据与源码hash见[28阶段档案索引](../research-final/index/stage_catalog.jsonl)。第28阶段已进行新GPU测量；旧阶段19/22做CPU复算，26做聚合复算，其余旧阶段本次REPORT_ONLY，不能说全历史GPU重验。

---

## 前史：2026-10-13 的 RTX 5080（4 轮，不计入上表）

T10 开始前一天，在另一台机器（RTX 5080）上先试了四轮。它们不并入 28 个T10阶段的编号，也不参与任何合并统计；机器、软件和读数见 [前史导读](RTX5080_STAGE.md)。

| 轮次 | 日期 | 做了什么 | 得到什么 | 限制 |
|---|---|---|---|---|
| R1 | 10-13 | 资源盘点、预注册、CPU 分析工具与合成数据自检 | 只读 CUDA 初始化成功；硬件测量 0 次、渲染 session 0 个 | 缺工具链、runner、renderer 与资产；CPU 自检不能代替硬件证据 |
| R2 | 10-13 | 离线恢复工具链与 Graphdeco 渲染器，测资源复用的调度原型 | 36 个 session、18,432 帧；候选比原生慢 42.4%，比负载均衡基线慢 26.9%；0 处输出不匹配 | 容量模型未校准；单 renderer、单卡；Xid 13/43 的根因没有证明 |
| R3 | 10-13 | 84 个 SM × 地址区域的静态采样，K=2 分组，两次新分配留出 | 留出预测 0.331%（区间 0.253–0.382%），低于冻结的 3% 门槛 | 弱正数既不是零，也不是可部署；地图没有部署，也没有接渲染器 |
| R4 | 10-13 | 把 R3 的图装进 Green 40/40/4，与 Native、置换聚合、盲选完整配对 | 192 MiB 普通负载慢 1.388%（+14.941 µs/epoch），`.cg` 慢 1.455%；小工作集有零散正数 | 四个 PRESSURE 种子与资格阶段重叠（已披露）；只覆盖 16/192 MiB 两种访问集 |

---

## 对应的原始记录

5080 四轮的代码与证据目录为 [experiments/rtx5080-20261013/](../experiments/rtx5080-20261013/)，原包和补充输出见 [5080 归档](../archive/rtx5080/README.md)。以下表格继续对应 T10。

每个阶段的报告都保持原文。归档中的路径以 `numa_gpu/` 开头；原下载和桌面交付在 `handoffs/`。按目录分包只是存储方式，不代表同一个包里的所有试验共享样本或统计口径。

| 阶段 | 归档包 | 文件清单 |
|---|---|---|
| 01、02 | `runs.tar.zst` | [runs.jsonl](../archive/manifests/runs.jsonl) |
| 03–06 | `op-fused.tar.zst` | [op-fused.jsonl](../archive/manifests/op-fused.jsonl) |
| 07、08 | `numa-first-v3.tar.zst` | [numa-first-v3.jsonl](../archive/manifests/numa-first-v3.jsonl) |
| 09 | `pc-handoff-t10.tar.zst` | [pc-handoff-t10.jsonl](../archive/manifests/pc-handoff-t10.jsonl) |
| 10 | `selective-reorder-t10.tar.zst` | [selective-reorder-t10.jsonl](../archive/manifests/selective-reorder-t10.jsonl) |
| 11 | `selective-reorder-repair-v2-t10.tar.zst` | [selective-reorder-repair-v2-t10.jsonl](../archive/manifests/selective-reorder-repair-v2-t10.jsonl) |
| 12 | `transient-f4-diag-t10.tar.zst` | [transient-f4-diag-t10.jsonl](../archive/manifests/transient-f4-diag-t10.jsonl) |
| 13 | `state-causality-t10.tar.zst` | [state-causality-t10.jsonl](../archive/manifests/state-causality-t10.jsonl) |
| 14 | `matched-pacing-t10.tar.zst` | [matched-pacing-t10.jsonl](../archive/manifests/matched-pacing-t10.jsonl) |
| 15 | `sm-topology-t10.tar.zst` | [sm-topology-t10.jsonl](../archive/manifests/sm-topology-t10.jsonl) |
| 16 | `address-gemm-t10.tar.zst` | [address-gemm-t10.jsonl](../archive/manifests/address-gemm-t10.jsonl) |
| 17 | `address-gemm-v2-t10.tar.zst` | [address-gemm-v2-t10.jsonl](../archive/manifests/address-gemm-v2-t10.jsonl) |
| 18 | `llm-decode-locality-t10.tar.zst` | [llm-decode-locality-t10.jsonl](../archive/manifests/llm-decode-locality-t10.jsonl) |
| 19 | `numa-locality-scheduling-t10.tar.zst` | [numa-locality-scheduling-t10.jsonl](../archive/manifests/numa-locality-scheduling-t10.jsonl) |
| 20 | `numa-affinity-fastpath-t10.tar.zst` | [numa-affinity-fastpath-t10.jsonl](../archive/manifests/numa-affinity-fastpath-t10.jsonl) |
| 21 | `numa-affinity-causal-t10.tar.zst` | [numa-affinity-causal-t10.jsonl](../archive/manifests/numa-affinity-causal-t10.jsonl) |
| 22 | `gpc-mask-t10.tar.zst` | [gpc-mask-t10.jsonl](../archive/manifests/gpc-mask-t10.jsonl) |
| 23 | `topology-affinity-t10.tar.zst` | [topology-affinity-t10.jsonl](../archive/manifests/topology-affinity-t10.jsonl) |
| 24 | `topology-tail-t10.tar.zst` | [topology-tail-t10.jsonl](../archive/manifests/topology-tail-t10.jsonl) |
| 25 | `topology-real-t10.tar.zst` | [topology-real-t10.jsonl](../archive/manifests/topology-real-t10.jsonl) |

**各阶段的报告入口**（在 `experiments/` 目录下）：

- 01：[DUAL_TOPOLOGY_PAPER_REPORT_t10.md](../experiments/reports/DUAL_TOPOLOGY_PAPER_REPORT_t10.md)
- 02：[T10_SUPPLEMENT_AND_PAPER_POSITION.md](../experiments/reports/T10_SUPPLEMENT_AND_PAPER_POSITION.md)
- 03：[OPERATOR_FUSED_SCHEDULING_REPORT_t10.md](../experiments/op-fused/reports/OPERATOR_FUSED_SCHEDULING_REPORT_t10.md)
- 04：[OPERATOR_FUSED_IMPLEMENTATION_REPORT_t10.md](../experiments/op-fused/recovery_20261015/reports/OPERATOR_FUSED_IMPLEMENTATION_REPORT_t10.md)
- 05：[OPERATOR_FUSED_IMPLEMENTATION_REPORT_t10.md](../experiments/op-fused/implementation/reports/OPERATOR_FUSED_IMPLEMENTATION_REPORT_t10.md)
- 06：[T10_SAME_Q_AND_BACKBONE_REPORT.md](../experiments/op-fused/implementation_same_q_v2/20261015T171030Z/reports/T10_SAME_Q_AND_BACKBONE_REPORT.md)
- 07：[NUMA_FIRST_V3_T10_REPORT.md](../experiments/numa-first-v3/NUMA_FIRST_V3_T10_REPORT.md)
- 08：[T10_NUMA_FROZEN_RULE_MECHANISM_REPORT.md](../experiments/numa-first-v3/T10_NUMA_FROZEN_RULE_MECHANISM_REPORT.md)
- 09：[T10_PC_HANDOFF_LLM_REPORT.md](../experiments/pc-handoff-t10/T10_PC_HANDOFF_LLM_REPORT.md)
- 10：[T10_SELECTIVE_REORDER_REPORT.md](../experiments/selective-reorder-t10/reports/T10_SELECTIVE_REORDER_REPORT.md)
- 11：[T10_SELECTIVE_REORDER_REPAIR_V2_REPORT.md](../experiments/selective-reorder-repair-v2-t10/reports/T10_SELECTIVE_REORDER_REPAIR_V2_REPORT.md)
- 12：[T10_TRANSIENT_AND_F4_DIAG_REPORT.md](../experiments/transient-f4-diag-t10/reports/T10_TRANSIENT_AND_F4_DIAG_REPORT.md)
- 13：[T10_STATE_CAUSALITY_REPORT.md](../experiments/state-causality-t10/reports/T10_STATE_CAUSALITY_REPORT.md)
- 14：[T10_MATCHED_PACING_REPORT.md](../experiments/matched-pacing-t10/reports/T10_MATCHED_PACING_REPORT.md)
- 15：[T10_SM_TOPOLOGY_AND_OPTIMIZATION_REPORT.md](../experiments/sm-topology-t10/reports/T10_SM_TOPOLOGY_AND_OPTIMIZATION_REPORT.md)
- 16：[ADDRESS_GEMM_REPORT.md](../experiments/address-gemm-t10/reports/ADDRESS_GEMM_REPORT.md)
- 17：[REPORT.md](../experiments/address-gemm-v2-t10/reports/REPORT.md)
- 18：[REPORT.md](../experiments/llm-decode-locality-t10/reports/REPORT.md)
- 19：[REPORT.md](../experiments/numa-locality-scheduling-t10/reports/REPORT.md)
- 20：[REPORT.md](../experiments/numa-affinity-fastpath-t10/reports/REPORT.md)
- 21：[REPORT.md](../experiments/numa-affinity-causal-t10/reports/REPORT.md)
- 22：[REPORT.md](../experiments/gpc-mask-t10/reports/REPORT.md)
- 23：[REPORT.md](../experiments/topology-affinity-t10/reports/REPORT.md)
- 24：[REPORT.md](../experiments/topology-tail-t10/reports/REPORT.md)
- 25：[REPORT.md](../experiments/topology-real-t10/reports/REPORT.md)

**前史（RTX 5080，2026-10-13）的报告入口**：

- R1：[AFFINITY_RENDER_OPPORTUNITY_REPORT.md](rtx5080/AFFINITY_RENDER_OPPORTUNITY_REPORT.md)
- R2：[RTX5080_RENDER_SCHEDULING_RESUMED_REPORT.md](rtx5080/RTX5080_RENDER_SCHEDULING_RESUMED_REPORT.md)
- R3：[STATIC_AFFINITY_SPECIALIZATION_REPORT.md](rtx5080/STATIC_AFFINITY_SPECIALIZATION_REPORT.md)
- R4：[STATIC_AFFINITY_CAUSAL_COMPLETION.md](rtx5080/STATIC_AFFINITY_CAUSAL_COMPLETION.md)
