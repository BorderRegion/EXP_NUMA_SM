# T10研究档案：28阶段总入口

本轮已按任务书的 **CONTROL_LIMITED分支完成**。管理员入口已实际使用，555/540/525MHz均未通过状态标准，已恢复动态时钟；完整长程矩阵没有运行。四个GQA锚的CAP完整耗时都未胜原N19。默认保留第19阶段快核，不自动开下一轮。

[最终研究报告](FINAL_RESEARCH_REPORT.md) · [导师简报](MENTOR_UPDATE.md) · [状态与恢复](ADMIN_AND_STATE.md) · [容量结果](GPC_CAPACITY_REPORT.md) · [真实算子结果](APPLICATION_REPORT.md)

## 探索图

![28阶段探索图](sources/figures/exploration_28.png)

图表示问题演进，阶段数不是独立样本数；不同阶段正数不能相加。

## 28阶段索引

|显示编号|目的|结论与反例|本轮复核级别|
|---|---|---|---|
|01|[公开资源分组 → 3DGS / CSR](sources/reports/DUAL_TOPOLOGY_PAPER_REPORT_t10.md)|E0–E4：T10 56 SM；Bonsai/Train 渲染与真实 CSR。M/N 耗时比 W1=1.1113、W2=1.2271；M/R 接近 1。 没有可部署增量；5070 Ti 未实测，E5 未触发。|REPORT_ONLY|
|02|[S0–S5 补充与强基线](sources/reports/T10_SUPPLEMENT_AND_PAPER_POSITION.md)|加入 Native 首尾锚、顺序轮换和经验匹配控制；W1 M/R=1.00116，W2=0.99691。 S3 内部匹配有条件效应，但 A/N=1.13160；S4 未触发。|REPORT_ONLY|
|03|[算子内调度方案与原生基线](sources/op-fused/reports/OPERATOR_FUSED_SCHEDULING_REPORT_t10.md)|156 个 case、936 个 case-block、4248 个 phase；候选覆盖为 0。 当时缺可修改主体；125/100 W 温控切换，不能称固定功耗结果。|REPORT_ONLY|
|04|[接入合同和固定功耗恢复](sources/op-fused/recovery_20261015/reports/OPERATOR_FUSED_IMPLEMENTATION_REPORT_t10.md)|完成 CPU adapter 合同与源码冻结；应用并核验 100 W 上限，保留风扇和过温保护。 阶段本身无新增 GPU 方法测量，依赖缺口随后解决。|REPORT_ONLY|
|05|[CUTLASS grouped 内部调度与融合](sources/op-fused/implementation/reports/OPERATOR_FUSED_IMPLEMENTATION_REPORT_t10.md)|FULL/同体强简单策略=0.8536，但 FULL/LIB=2.0335；完整层 F1S1/LIB=1.8340。 FULL 冻结 qcap=1，与 ABL 别名；同体正结果不能归因于新增自适应信息。|REPORT_ONLY|
|06|[同 q 归因与数学主体复核](sources/op-fused/implementation_same_q_v2/20261015T171030Z/reports/T10_SAME_Q_AND_BACKBONE_REPORT.md)|新确认精简 q1/CACHEq1=0.9977，精简 q1/LIB=1.3682；层精简/LIB=1.3537。 识别少量普通实现开销；数学主体仍落后成熟库。|REPORT_ONLY|
|07|[NUMA-first：逐 SM 地址探针与消费者](sources/numa-first-v3/NUMA_FIRST_V3_T10_REPORT.md)|粗 28+28 分组主条件未稳定；细化 2-SM 后局部小工作集差异可复现。 9 个消费者条件没有 M/N 与 M/T 的可靠正部署证据；不能把探针地图直接当应用地图。|REPORT_ONLY|
|08|[冻结 0x33 规则的低/高并发机制](sources/numa-first-v3/T10_NUMA_FROZEN_RULE_MECHANISM_REPORT.md)|924/924 phase；低并发 L1 joint log 优势约 0.9417%，L8 约 1.0095%。 高并发 H1 约 0.0218%、区间跨零；clean 完整请求净收益未建立。|REPORT_ONLY|
|09|[Producer–consumer handoff 与 LLM 形状](sources/pc-handoff-t10/T10_PC_HANDOFF_LLM_REPORT.md)|真实 CUTLASS split-K partial 生产与归并；M 对 cuBLAS 的延迟节省为 −26.42%，对 CORE 为 −2.97%。 冻结 M 与简单 G 同图、无新增选择信息；Attention PC adapter 缺失。|REPORT_ONLY|
|10|[选择性重排：允许回退 Native](sources/selective-reorder-t10/reports/T10_SELECTIVE_REORDER_REPORT.md)|完整有限矩阵和部署；H=1024 的正式形状 BASE/SHAPE/RESOURCE 都选 LIB。 事后免费 oracle 有空间，但未实现资源信息增量。|REPORT_ONLY|
|11|[选择器修复 V2 与 A/A 审计](sources/selective-reorder-repair-v2-t10/reports/T10_SELECTIVE_REORDER_REPAIR_V2_REPORT.md)|102/168 个 A/A quartet 偏移超过 5%；RESOURCE 对 SHAPE 时间节省 −0.588%，对 LIB −14.601%。 稳定性未修复；RESOURCE/SHAPE 在新输入 0/16 动作分歧，不能归因于资源信息。|REPORT_ONLY|
|12|[起始瞬态与 F4 退化](sources/transient-f4-diag-t10/reports/T10_TRANSIENT_AND_F4_DIAG_REPORT.md)|144 单元完成；R_G017 约 460–1010 μs 跳变并非只在起始；V16 与 F4 的 SINGLE 选择退化。 READY_RING4 未恢复 1% 分辨率；CUPTI 将 F4 增量定位到第一 GEMM，硬件根因未闭合。|REPORT_ONLY|
|13|[运行状态与可逆提交节奏](sources/state-causality-t10/reports/T10_STATE_CAUSALITY_REPORT.md)|100 μs 请求间隔：主六块净完成率 +20.67%，辅助复验 −5.95%。 单请求缩短不等于吞吐提高；频率/缓存根因未隔离，不能只引用主实验正数。|REPORT_ONLY|
|14|[统一准备流程的节奏复验](sources/matched-pacing-t10/reports/T10_MATCHED_PACING_REPORT.md)|同准备四块全部无净收益：1 Hz 组 −10.53%，20 Hz 组 −7.89%。 等待成本大于处理节省；旧慢态未充分复现，不给稳定提速结论。|REPORT_ONLY|
|15|[逐 SM 通信矩阵与地址调度原型](sources/sm-topology-t10/reports/T10_SM_TOPOLOGY_AND_OPTIMIZATION_REPORT.md)|同址周期相关 0.981、跨位置约 0.078；通信事件时间相对固定/随机/盲配对减少 2.458%/1.101%/0.478%。 这是通信原型，尚非 GEMM 或 LLM 提速，也不是物理连线图。|REPORT_ONLY|
|16|[地址感知归并接入真实 GEMM](sources/address-gemm-t10/reports/ADDRESS_GEMM_REPORT.md)|92160 次完整确认请求；ADDRESS 比同核固定减少 0.1795%，但比原 CUTLASS 增加 1.9429%。 计入完整 kernel 后没有净收益；CPU 建表加速不能算 GPU 提速。|REPORT_ONLY|
|17|[页内队列、融合与更强 GEMM 配方](sources/address-gemm-v2-t10/reports/REPORT.md)|地址队列比普通 GEMM 慢 1.278%；普通 D13 配方比 cuBLAS 时间减少 8.616%。 可用收益来自普通配方选择；种子重用与 sanitizer 范围限制完整披露。|REPORT_ONLY|
|18|[GQA decode 快核与 KV 写入融合](sources/llm-decode-locality-t10/reports/REPORT.md)|六形状相对预选本机库 GPU 时间减少 33.554%–55.323%；地址偏好比同队列无偏好慢 0.962%。 共享 KV、序列分片和融合有效；不是 NUMA 收益、整模型 token/s 或 SOTA 证明。|REPORT_ONLY|
|19|[NUMA 风格调度与向量化快路径](sources/numa-locality-scheduling-t10/reports/REPORT.md)|四组 KV 写入+Attention 比预选旧实现减少 25.157%–37.800%；地址偏好比无偏好慢 1.584%。 16 字节搬运和普通任务分配有效，NUMA 本身未贡献额外收益；阶段百分比不可相加。|RAW_RECOMPUTED|
|20|[冻结快核后：Softmax SM 配对](sources/numa-affinity-fastpath-t10/reports/REPORT.md)|V=131072、页17热输入，同核改配对比固定减少 2.157%，比随机平均减少 1.024%。 改成连续32次后比固定慢 1.481%；条件正效应未转成可通用地址调度。|REPORT_ONLY|
|21|[均衡工作与固定归并者因果对照](sources/numa-affinity-causal-t10/reports/REPORT.md)|OLD/BAL/FIX/BOTH、两词表四条件；16 项地址主对照未过门槛，新完整核比旧快核慢 2.801%–4.282%。 工作不均、归并者、编译入口/Graph 和运行节奏不能混为裸 SM 距离。|REPORT_ONLY|
|22|[直接读取真实 GPC/TPC 屏蔽分布](sources/gpc-mask-t10/reports/REPORT.md)|同版本 NVIDIA RM 接口三进程一致：物理 GPC0–5 为 10/12/12/10/0/12 SM；非均匀屏蔽。 确定资源拓扑，不确定平面几何距离；只读查询不是性能实验。|RAW_RECOMPUTED|
|23|[按真实同 TPC / 同 GPC / 跨 GPC 比较](sources/topology-affinity-t10/reports/REPORT.md)|页17孤立往返约 1160.6/1178.9/1174.3 ns；同 TPC 小幅优势。热输入调度相对原配对净 +0.418%。 仍输冻结随机、错误地址和混合地址；并发偏好可反转，没有稳定 GPC NUMA 域证据。|REPORT_ONLY|
|24|[完整通信尾部代理与地址放置](sources/topology-tail-t10/reports/REPORT.md)|132 候选、2开发+6确认；JOINT 热输入净 −0.360%，静态 BLIND54 +0.677%、6/6正。 代理排序预测弱；fresh 小正平均由单进程长尾拉起。保留静态规则为强基线。|REPORT_ONLY|
|25|[新固定基线与低成本真实核采样](sources/topology-real-t10/reports/REPORT.md)|BASE54 复验热输入 +0.8318%、重写 +0.3346%，各6/6正；TUNED 对 BASE 净 −0.2728%/−0.2563%。 未扣校准平均也无正收益；保留 BASE54，停止当前 Softmax 同类搜索。|REPORT_ONLY|
|26|[GPC竞争、地址相关性与GQA共置](sources/gpc-contention-gqa-t10/runs/20261019T041515Z/reports/T10_GPC_CONTENTION_GQA_REPORT.md)|热读分散有局部优势；完整GQA效应小；10/46静态共置不能越过强简单基线。 同卡动态100W；局部SM数及工作集不同，不能推广物理NUMA。|AGGREGATES_RECOMPUTED|
|27|[资源份额与尾部释放收束](sources/quota-tail-closure-t10/runs/20261019T064852Z/reports/T10_QUOTA_TAIL_CLOSURE_REPORT.md)|LONG释放/固定耗时−24.972%；冻结JOINT/最强原生+0.633%，97.5%区间跨零；PACK/NEUTRAL−1.601%。 PACK对强串行区间跨零；确认后不重新选择；RAGGED冻结为串行alias。|REPORT_ONLY|
|28|[同GPC容量饱和与真实GQA静态完整worker分工；最后一次有限验证及归档](FINAL_RESEARCH_REPORT.md)|CAP slower than N19 on all four anchors in two dynamic blocks; full fixed-state hypothesis condition-limited some partition contrasts positive, but not beyond N19; read-service total capacity nearly flat10→12 in these samples; no strong inference|GPU_RERUN|

## 怎样检索和复算

- `index/stage_catalog.jsonl`：稳定stage_uid、原目录/run、状态、数学体/入口hash、真实负载范围、限制及下一步。原编号只显示。
- `index/claims_and_evidence.jsonl`：结论、精确来源行、反例和不能推出什么；C01–C05是五个必须单列的主张。
- `index/artifact_manifest.jsonl`：关键旧文件hash与是否随包；`historical_raw_availability.jsonl`说明旧manifest中路径目前是否存在。旧大raw摘要为INHERITED，60个确定性抽样hash均匹配，不是全量数值复核。
- 第19阶段在隔离输出目录重跑原CPU复算，3份派生JSON完全一致；第22阶段重算原RM映射；第26阶段重算签名SM→GPC块均值。其余旧阶段明确REPORT_ONLY，原审计可追溯但本轮未伪称重跑。
- 本轮CPU入口：`python3 last_run/final-gpc-capacity-t10/src/recompute_final.py`。只解析已有raw，不启动CUDA；需要NumPy。
- 唯一推荐GQA接口见[FAST_GQA](reusable/FAST_GQA.md)，旧搜索路径见[deprecated_paths](reusable/deprecated_paths.md)。

## 包的范围

`REVIEW_SMALL.zip`含报告、索引、全部本轮主比较raw、NA/alias、源码和CPU复算，不含GPU二进制。`REPRODUCE_FULL.zip`再包含本轮与N19关键二进制。两者都通过CRC和逐文件manifest校验。

**历史大raw以本地原件/旧归档manifest引用，不重复打包；FULL不是全部28阶段可离线独立复现包。** 没有下载缺失归档或上传GitHub/Drive。第三方CUDA/PyTorch/驱动/toolchain不随包。来源原件只读保留；分享副本只移除无关进程完整参数，脱敏记录见index/SHARING_REDACTIONS.json。
