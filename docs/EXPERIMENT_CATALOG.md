# 全部探索阶段索引

按研究推进顺序列出 25 个阶段；同一目录可包含数个阶段，一个阶段也可有开发、资格、失败、正式与补充 run。**阶段数不是独立样本数。** 全量文件目录见 [archive/INDEX.json](../archive/INDEX.json)，包括未被本文引用的失败和负结果。

时间为 2026 年，具体 UTC run 标识以原始文件为准。表内时间比小于 1 才快；“时间减少/节省”为正才快，吞吐、速度比、log 交互不可直接混算。

| 阶段 | 日期 | 问题 / 报告 | 实际结果 | 限制 / 下一步理由 |
|---|---|---|---|---|
| 01 | 10-14/15 | [公开资源分组 → 3DGS / CSR](../experiments/reports/DUAL_TOPOLOGY_PAPER_REPORT_t10.md) | E0–E4：T10 56 SM；Bonsai/Train 渲染与真实 CSR。M/N 耗时比 W1=1.1113、W2=1.2271；M/R 接近 1。 | 没有可部署增量；5070 Ti 未实测，E5 未触发。 |
| 02 | 10-15 | [S0–S5 补充与强基线](../experiments/reports/T10_SUPPLEMENT_AND_PAPER_POSITION.md) | 加入 Native 首尾锚、顺序轮换和经验匹配控制；W1 M/R=1.00116，W2=0.99691。 | S3 内部匹配有条件效应，但 A/N=1.13160；S4 未触发。 |
| 03 | 10-15 | [算子内调度方案与原生基线](../experiments/op-fused/reports/OPERATOR_FUSED_SCHEDULING_REPORT_t10.md) | 156 个 case、936 个 case-block、4248 个 phase；候选覆盖为 0。 | 当时缺可修改主体；125/100 W 温控切换，不能称固定功耗结果。 |
| 04 | 10-15 | [接入合同和固定功耗恢复](../experiments/op-fused/recovery_20261015/reports/OPERATOR_FUSED_IMPLEMENTATION_REPORT_t10.md) | 完成 CPU adapter 合同与源码冻结；应用并核验 100 W 上限，保留风扇和过温保护。 | 阶段本身无新增 GPU 方法测量，依赖缺口随后解决。 |
| 05 | 10-15/16 | [CUTLASS grouped 内部调度与融合](../experiments/op-fused/implementation/reports/OPERATOR_FUSED_IMPLEMENTATION_REPORT_t10.md) | FULL/同体强简单策略=0.8536，但 FULL/LIB=2.0335；完整层 F1S1/LIB=1.8340。 | FULL 冻结 qcap=1，与 ABL 别名；同体正结果不能归因于新增自适应信息。 |
| 06 | 10-16 | [同 q 归因与数学主体复核](../experiments/op-fused/implementation_same_q_v2/20261015T171030Z/reports/T10_SAME_Q_AND_BACKBONE_REPORT.md) | 新确认精简 q1/CACHEq1=0.9977，精简 q1/LIB=1.3682；层精简/LIB=1.3537。 | 识别少量普通实现开销；数学主体仍落后成熟库。 |
| 07 | 10-16 | [NUMA-first：逐 SM 地址探针与消费者](../experiments/numa-first-v3/NUMA_FIRST_V3_T10_REPORT.md) | 粗 28+28 分组主条件未稳定；细化 2-SM 后局部小工作集差异可复现。 | 9 个消费者条件没有 M/N 与 M/T 的可靠正部署证据；不能把探针地图直接当应用地图。 |
| 08 | 10-16 | [冻结 0x33 规则的低/高并发机制](../experiments/numa-first-v3/T10_NUMA_FROZEN_RULE_MECHANISM_REPORT.md) | 924/924 phase；低并发 L1 joint log 优势约 0.9417%，L8 约 1.0095%。 | 高并发 H1 约 0.0218%、区间跨零；clean 完整请求净收益未建立。 |
| 09 | 10-16/17 | [Producer–consumer handoff 与 LLM 形状](../experiments/pc-handoff-t10/T10_PC_HANDOFF_LLM_REPORT.md) | 真实 CUTLASS split-K partial 生产与归并；M 对 cuBLAS 的延迟节省为 −26.42%，对 CORE 为 −2.97%。 | 冻结 M 与简单 G 同图、无新增选择信息；Attention PC adapter 缺失。 |
| 10 | 10-17 | [选择性重排：允许回退 Native](../experiments/selective-reorder-t10/reports/T10_SELECTIVE_REORDER_REPORT.md) | 完整有限矩阵和部署；H=1024 的正式形状 BASE/SHAPE/RESOURCE 都选 LIB。 | 事后免费 oracle 有空间，但未实现资源信息增量。 |
| 11 | 10-17 | [选择器修复 V2 与 A/A 审计](../experiments/selective-reorder-repair-v2-t10/reports/T10_SELECTIVE_REORDER_REPAIR_V2_REPORT.md) | 102/168 个 A/A quartet 偏移超过 5%；RESOURCE 对 SHAPE 时间节省 −0.588%，对 LIB −14.601%。 | 稳定性未修复；RESOURCE/SHAPE 在新输入 0/16 动作分歧，不能归因于资源信息。 |
| 12 | 10-17 | [起始瞬态与 F4 退化](../experiments/transient-f4-diag-t10/reports/T10_TRANSIENT_AND_F4_DIAG_REPORT.md) | 144 单元完成；R_G017 约 460–1010 μs 跳变并非只在起始；V16 与 F4 的 SINGLE 选择退化。 | READY_RING4 未恢复 1% 分辨率；CUPTI 将 F4 增量定位到第一 GEMM，硬件根因未闭合。 |
| 13 | 10-17 | [运行状态与可逆提交节奏](../experiments/state-causality-t10/reports/T10_STATE_CAUSALITY_REPORT.md) | 100 μs 请求间隔：主六块净完成率 +20.67%，辅助复验 −5.95%。 | 单请求缩短不等于吞吐提高；频率/缓存根因未隔离，不能只引用主实验正数。 |
| 14 | 10-17 | [统一准备流程的节奏复验](../experiments/matched-pacing-t10/reports/T10_MATCHED_PACING_REPORT.md) | 同准备四块全部无净收益：1 Hz 组 −10.53%，20 Hz 组 −7.89%。 | 等待成本大于处理节省；旧慢态未充分复现，不给稳定提速结论。 |
| 15 | 10-17 | [逐 SM 通信矩阵与地址调度原型](../experiments/sm-topology-t10/reports/T10_SM_TOPOLOGY_AND_OPTIMIZATION_REPORT.md) | 同址周期相关 0.981、跨位置约 0.078；通信事件时间相对固定/随机/盲配对减少 2.458%/1.101%/0.478%。 | 这是通信原型，尚非 GEMM 或 LLM 提速，也不是物理连线图。 |
| 16 | 10-17 | [地址感知归并接入真实 GEMM](../experiments/address-gemm-t10/reports/ADDRESS_GEMM_REPORT.md) | 92160 次完整确认请求；ADDRESS 比同核固定减少 0.1795%，但比原 CUTLASS 增加 1.9429%。 | 计入完整 kernel 后没有净收益；CPU 建表加速不能算 GPU 提速。 |
| 17 | 10-17 | [页内队列、融合与更强 GEMM 配方](../experiments/address-gemm-v2-t10/reports/REPORT.md) | 地址队列比普通 GEMM 慢 1.278%；普通 D13 配方比 cuBLAS 时间减少 8.616%。 | 可用收益来自普通配方选择；种子重用与 sanitizer 范围限制完整披露。 |
| 18 | 10-17 | [GQA decode 快核与 KV 写入融合](../experiments/llm-decode-locality-t10/reports/REPORT.md) | 六形状相对预选本机库 GPU 时间减少 33.554%–55.323%；地址偏好比同队列无偏好慢 0.962%。 | 共享 KV、序列分片和融合有效；不是 NUMA 收益、整模型 token/s 或 SOTA 证明。 |
| 19 | 10-18 | [NUMA 风格调度与向量化快路径](../experiments/numa-locality-scheduling-t10/reports/REPORT.md) | 四组 KV 写入+Attention 比预选旧实现减少 25.157%–37.800%；地址偏好比无偏好慢 1.584%。 | 16 字节搬运和普通任务分配有效，NUMA 本身未贡献额外收益；阶段百分比不可相加。 |
| 20 | 10-18 | [冻结快核后：Softmax SM 配对](../experiments/numa-affinity-fastpath-t10/reports/REPORT.md) | V=131072、页17热输入，同核改配对比固定减少 2.157%，比随机平均减少 1.024%。 | 改成连续32次后比固定慢 1.481%；条件正效应未转成可通用地址调度。 |
| 21 | 10-18 | [均衡工作与固定归并者因果对照](../experiments/numa-affinity-causal-t10/reports/REPORT.md) | OLD/BAL/FIX/BOTH、两词表四条件；16 项地址主对照未过门槛，新完整核比旧快核慢 2.801%–4.282%。 | 工作不均、归并者、编译入口/Graph 和运行节奏不能混为裸 SM 距离。 |
| 22 | 10-18 | [直接读取真实 GPC/TPC 屏蔽分布](../experiments/gpc-mask-t10/reports/REPORT.md) | 同版本 NVIDIA RM 接口三进程一致：物理 GPC0–5 为 10/12/12/10/0/12 SM；非均匀屏蔽。 | 确定资源拓扑，不确定平面几何距离；只读查询不是性能实验。 |
| 23 | 10-18 | [按真实同 TPC / 同 GPC / 跨 GPC 比较](../experiments/topology-affinity-t10/reports/REPORT.md) | 页17孤立往返约 1160.6/1178.9/1174.3 ns；同 TPC 小幅优势。热输入调度相对原配对净 +0.418%。 | 仍输冻结随机、错误地址和混合地址；并发偏好可反转，没有稳定 GPC NUMA 域证据。 |
| 24 | 10-18 | [完整通信尾部代理与地址放置](../experiments/topology-tail-t10/reports/REPORT.md) | 132 候选、2开发+6确认；JOINT 热输入净 −0.360%，静态 BLIND54 +0.677%、6/6正。 | 代理排序预测弱；fresh 小正平均由单进程长尾拉起。保留静态规则为强基线。 |
| 25 | 10-18 | [新固定基线与低成本真实核采样](../experiments/topology-real-t10/reports/REPORT.md) | BASE54 复验热输入 +0.8318%、重写 +0.3346%，各6/6正；TUNED 对 BASE 净 −0.2728%/−0.2563%。 | 未扣校准平均也无正收益；保留 BASE54，停止当前 Softmax 同类搜索。 |

## 对应原始记录

每个报告保持原文。完整归档中的路径以 `numa_gpu/` 开头；原下载与桌面交付在 `handoffs/`。按目录分包是存储安排，不意味着同一个包的所有试验共享样本或统计合同。

- 01：`runs.tar.zst`；[runs 文件清单](../archive/manifests/runs.jsonl)。
- 02：`runs.tar.zst`；[runs 文件清单](../archive/manifests/runs.jsonl)。
- 03：`op-fused.tar.zst`；[op-fused 文件清单](../archive/manifests/op-fused.jsonl)。
- 04：`op-fused.tar.zst`；[op-fused 文件清单](../archive/manifests/op-fused.jsonl)。
- 05：`op-fused.tar.zst`；[op-fused 文件清单](../archive/manifests/op-fused.jsonl)。
- 06：`op-fused.tar.zst`；[op-fused 文件清单](../archive/manifests/op-fused.jsonl)。
- 07：`numa-first-v3.tar.zst`；[numa-first-v3 文件清单](../archive/manifests/numa-first-v3.jsonl)。
- 08：`numa-first-v3.tar.zst`；[numa-first-v3 文件清单](../archive/manifests/numa-first-v3.jsonl)。
- 09：`pc-handoff-t10.tar.zst`；[pc-handoff-t10 文件清单](../archive/manifests/pc-handoff-t10.jsonl)。
- 10：`selective-reorder-t10.tar.zst`；[selective-reorder-t10 文件清单](../archive/manifests/selective-reorder-t10.jsonl)。
- 11：`selective-reorder-repair-v2-t10.tar.zst`；[selective-reorder-repair-v2-t10 文件清单](../archive/manifests/selective-reorder-repair-v2-t10.jsonl)。
- 12：`transient-f4-diag-t10.tar.zst`；[transient-f4-diag-t10 文件清单](../archive/manifests/transient-f4-diag-t10.jsonl)。
- 13：`state-causality-t10.tar.zst`；[state-causality-t10 文件清单](../archive/manifests/state-causality-t10.jsonl)。
- 14：`matched-pacing-t10.tar.zst`；[matched-pacing-t10 文件清单](../archive/manifests/matched-pacing-t10.jsonl)。
- 15：`sm-topology-t10.tar.zst`；[sm-topology-t10 文件清单](../archive/manifests/sm-topology-t10.jsonl)。
- 16：`address-gemm-t10.tar.zst`；[address-gemm-t10 文件清单](../archive/manifests/address-gemm-t10.jsonl)。
- 17：`address-gemm-v2-t10.tar.zst`；[address-gemm-v2-t10 文件清单](../archive/manifests/address-gemm-v2-t10.jsonl)。
- 18：`llm-decode-locality-t10.tar.zst`；[llm-decode-locality-t10 文件清单](../archive/manifests/llm-decode-locality-t10.jsonl)。
- 19：`numa-locality-scheduling-t10.tar.zst`；[numa-locality-scheduling-t10 文件清单](../archive/manifests/numa-locality-scheduling-t10.jsonl)。
- 20：`numa-affinity-fastpath-t10.tar.zst`；[numa-affinity-fastpath-t10 文件清单](../archive/manifests/numa-affinity-fastpath-t10.jsonl)。
- 21：`numa-affinity-causal-t10.tar.zst`；[numa-affinity-causal-t10 文件清单](../archive/manifests/numa-affinity-causal-t10.jsonl)。
- 22：`gpc-mask-t10.tar.zst`；[gpc-mask-t10 文件清单](../archive/manifests/gpc-mask-t10.jsonl)。
- 23：`topology-affinity-t10.tar.zst`；[topology-affinity-t10 文件清单](../archive/manifests/topology-affinity-t10.jsonl)。
- 24：`topology-tail-t10.tar.zst`；[topology-tail-t10 文件清单](../archive/manifests/topology-tail-t10.jsonl)。
- 25：`topology-real-t10.tar.zst`；[topology-real-t10 文件清单](../archive/manifests/topology-real-t10.jsonl)。
