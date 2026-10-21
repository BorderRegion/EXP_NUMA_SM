# T10 同 q 归因与数学主体复核（v2）

本轮已经完成预注册有限矩阵。精简 q1 / 同 q CACHE 在新确认输入上为 **0.9977 [0.9964, 0.9991]**；旧 FULLq1 / 同 q CACHE 为 **1.0062 [1.0049, 1.0076]**。这比较的是相同 tile/worker 序列下的实现开销，不是两种自适应方法。

精简 q1 / 成熟 LIB：已知回归 **1.6872 [1.6362, 1.7696]**，新合成确认 **1.3682 [1.3630, 1.3741]**。完整 post-route 层按实际输出等待时间，精简版 / LIB **1.3537 [1.2464, 1.4219]**，精简版 / 同 q CACHE **0.9985 [0.9975, 0.9995]**。数值小于 1 才表示更快，不能把时间比误读为加速倍数。

本轮与旧轮的 case 集合、种子与计时协议不同。新比值不能与旧 2.03×/1.83× 直接相减，不能把换了比较范围造成的差别称为工程提速。

研究标记：`METHOD_EVIDENCE_UNRESOLVED / NO_NEW_ADAPTIVE_INFORMATION_IMPLEMENTED / BACKBONE_GAP_REMAINS / Q1_IMPLEMENTATION_OVERHEAD_FOUND`。这里没有新增自适应规则；q1-minimal 是去掉无效状态的普通 N-panel 遍历基线。是否值得工程部署和是否形成新论文方法，是两个需要分别回答的问题。

## 执行范围与选型

- 接受附件任务范围，保留旧数据、旧冻结、旧 ZIP 与旧账本前缀。本轮无新网络、安装、SSH、驱动或功耗策略修改。
- 12 个新机制开发输入 × 3 个进程块，覆盖三组 K/N 和四种分布；最多四个成熟 SM75 配方，全局同体选型。旧结构均视为已见回归。
- 冻结配方 **r0**、固定 q **1**、库 **PER_EXPERT_GRAPH**。选择时刻 `2026-10-15T17:34:25.147140+00:00`，规则、所有开发均值见 `BODY_AND_BASELINE_FREEZE_V2.json`。
- 开发 CORE/LIB = **1.4266**，工程阈值 1.25；因此采用 **弱主体缩减分支：6 个已知回归 + 6 个新确认**，各 6 个进程块。没有使用确认计时改配方。
- 4 个预定完整层 × 6 块；局部融合 4 层 × 3 块 × 4 格；输入 ring 2 层 × 3 块 × 3 策略 × 2 模式（若可选资格失败则明确跳过，见原始状态）。
- 所有基线共享 Graph、共同配方与同体 worker 规则；只采用一个全局配方，没有给候选单独按测试 shape 调优。

## 同 q 对照的结果

**已知回归：**

| 比较：耗时比，小于 1 更快 | 比值 [探索性 95% 区间] |
|---|---|
| FULL_Q1_LEGACY/CACHE_Q1_LEGACY | 0.9910 [0.9591, 1.0087] |
| Q1_MINIMAL/CACHE_Q1_LEGACY | 1.0099 [0.9553, 1.0708] |
| Q1_MINIMAL/CORE_ORIGINAL | 0.8865 [0.8606, 0.9311] |
| Q1_MINIMAL/CACHE_FIXED_BEST | 1.0099 [0.9553, 1.0708] |
| Q1_MINIMAL/PER_EXPERT_GRAPH | 1.6872 [1.6362, 1.7696] |


**新合成输入确认：**

| 比较：耗时比，小于 1 更快 | 比值 [探索性 95% 区间] |
|---|---|
| FULL_Q1_LEGACY/CACHE_Q1_LEGACY | 1.0062 [1.0049, 1.0076] |
| Q1_MINIMAL/CACHE_Q1_LEGACY | 0.9977 [0.9964, 0.9991] |
| Q1_MINIMAL/CORE_ORIGINAL | 1.0018 [1.0000, 1.0038] |
| Q1_MINIMAL/CACHE_FIXED_BEST | 0.9977 [0.9964, 0.9991] |
| Q1_MINIMAL/PER_EXPERT_GRAPH | 1.3682 [1.3630, 1.3741] |


完整等价/成本卡见 `SAME_Q_SEMANTICS_CARD.md`。原生 r→(r//gn,r%gn)，三个 q1 版本 r→(r%gm,r//gm)。同样的前缀和 W 意味着问题序列、tile 序列、worker 归属相同。Q1_MINIMAL 继承原生问题发现和 advance，没有 packet/waves/K-budget 字段、总量规约、sideband 或外部列表。

FULLq1 仍保留通用实现的总 tile/K-budget 开销，CACHEq1 仍保留 packet 状态。因此其与精简版的差异可指向实现或代码生成；不能称为自适应信息收益。若 CACHE_FIXED_BEST 与 CACHEq1 重合，原始日志只计时一次并用 alias 引用。

## 数学主体：有限修复与归因

仅新增 32×64×32、64×64×32 两种成熟实例，保留 32×128×32 与 64×128×32。BN 变化同步传到 host 总 tile、覆盖、packet、sideband 与元数据；work_budget=128 K tiles 未变。

冻结 CORE 相对旧 r0 的开发耗时比：**STRUCTURAL_ALIAS：仍为 r0**。这是数学配方工程变化，不能计作调度方法的收益。

6 个结构代表单 problem，各 3 个进程块，统一 FP16 输入/输出、FP32 累积、row-major、alpha=1、beta=0；普通 GEMM 显式 split-K=1，仅用于诊断。

| 比较：耗时比，小于 1 更快 | 比值 [探索性 95% 区间] |
|---|---|
| SINGLE_r0/PER_EXPERT_GRAPH | 1.2587 [1.2552, 1.2652] |
| GROUPED_CORE_r0/PER_EXPERT_GRAPH | 1.9140 [1.9018, 1.9254] |
| GROUPED_MINIMAL_r0/PER_EXPERT_GRAPH | 1.4595 [1.3313, 1.5350] |
| SINGLE_r1/PER_EXPERT_GRAPH | 1.2523 [1.2436, 1.2584] |
| GROUPED_CORE_r1/PER_EXPERT_GRAPH | 1.7293 [1.7160, 1.7378] |
| GROUPED_MINIMAL_r1/PER_EXPERT_GRAPH | 1.2798 [1.2764, 1.2839] |
| SINGLE_r2/PER_EXPERT_GRAPH | 1.3960 [1.3838, 1.4064] |
| GROUPED_CORE_r2/PER_EXPERT_GRAPH | 2.0729 [2.0591, 2.0874] |
| GROUPED_MINIMAL_r2/PER_EXPERT_GRAPH | 1.6933 [1.6801, 1.7013] |
| SINGLE_r3/PER_EXPERT_GRAPH | 1.4438 [1.4331, 1.4521] |
| GROUPED_CORE_r3/PER_EXPERT_GRAPH | 1.8332 [1.8166, 1.8477] |
| GROUPED_MINIMAL_r3/PER_EXPERT_GRAPH | 1.2736 [1.2616, 1.2811] |
| GROUPED_CORE_r0/SINGLE_r0 | 1.5206 [1.5134, 1.5340] |
| GROUPED_MINIMAL_r0/SINGLE_r0 | 1.1595 [1.0607, 1.2133] |
| GROUPED_CORE_r1/SINGLE_r1 | 1.3809 [1.3780, 1.3847] |
| GROUPED_MINIMAL_r1/SINGLE_r1 | 1.0220 [1.0193, 1.0264] |
| GROUPED_CORE_r2/SINGLE_r2 | 1.4849 [1.4736, 1.4932] |
| GROUPED_MINIMAL_r2/SINGLE_r2 | 1.2130 [1.2078, 1.2170] |
| GROUPED_CORE_r3/SINGLE_r3 | 1.2697 [1.2640, 1.2775] |
| GROUPED_MINIMAL_r3/SINGLE_r3 | 0.8821 [0.8803, 0.8858] |


普通单 GEMM 的 Identity swizzle 使用二维网格（N=1 时 x 对应 M、y 对应 N），grouped 使用一维持续 worker；即使 tile 配方相同也不是相同 CTA 发射顺序。

同 tile 普通 GEMM 与 grouped 的区别同时包含入口、持续执行方式、访问组织和资源生成，不能用一个比值单独证明 visitor 的指令成本。若普通 GEMM 仍比 LIB 慢，损失至少不完全来自多 expert；若普通明显快而 grouped 慢，则支持进一步检查 grouped 持续循环/资源，而不是仅宣称 Tensor Core 已使用就足够高效。

资源/SASS见 `SOURCE_AND_SASS_AUDIT.json`、`derived/resources.json`。四个 visitor 共用每配方中最小 active-block 上限得到的 worker 数；静态寄存器和 occupancy 上限不是 achieved occupancy。旧 packet/header 保持原字节，MMA/mainloop/epilogue 没有重写。没有 maxrregcount、精度降低或 fast-math。

Host-precompute grouped 未接入：需要额外 host descriptor/workspace 生命周期和不同入口资格，本轮保留四项核心诊断与有限配方范围。未新增 profiler 安装/硬件 counter；无法给出缓存命中、DRAM 或动态 spill 根因。

## 已经能回答的归因问题

1. FULLq1 与 CACHEq1 在新确认上的残余差异约 0.62%，方向是 FULL 更慢；已知回归区间跨 1。这不支持 FULL 使用新信息带来收益。
2. 精简版在新确认上比 CACHEq1 少约 0.23% 时间，属于很小的实现成本差异；已知回归没有分开的证据，不能推广成普遍优化。
3. 普通 N-panel 遍历在已知回归平均比原生 CORE 少约 11.4% 时间；新确认 MIN/CORE 接近 1，说明价值依赖具体 shape，不能将旧正例当全域规律。
4. 原配方单 problem 普通 GEMM/LIB 约 1.26，grouped CORE/LIB 约 1.91。访问组织/持续 worker/入口资源和数学实例都有证据相关，单独缓存或物理 SM 根因仍未知。
5. 两个新增小 tile 未赢开发选型，寄存器更少并未转成整体更快；冻结仍为 r0。未启用 shape-bin 或候选独享调优。
6. 同融合层的差别见下表，融合与 q1 实现开销分别计量；没有新自适应信息。
7. 已测热重放与 activation ring，未测冷启动或完整在线 router。
8. grouped 计时 DAG 是一个计算 kernel；最小版无 planner、sideband、调度 D2H 或内部等待。完整层的边界都计时，源文件与 Graph 节点保留。
9. 当前新增内容是严谨基线与有限实现/融合工程；不是已识别的新调度方法贡献。
10. 向 5070Ti 带走合同和反例，重建该机合法高效主体；T10 配方与性能数值不能直接外推。

## 完整层与局部融合

下表为每次请求含结果边界等待的 CPU-ready 时间，不是仅 GEMM kernel 时间。输入路由是固定 post-route 描述符，六个 payload/weight 种子对应三组重复路由。

| 比较：耗时比，小于 1 更快 | 比值 [探索性 95% 区间] |
|---|---|
| FULL_Q1_LEGACY/CACHE_Q1_LEGACY | 1.0062 [1.0043, 1.0090] |
| Q1_MINIMAL/CACHE_Q1_LEGACY | 0.9985 [0.9975, 0.9995] |
| Q1_MINIMAL/LIB | 1.3537 [1.2464, 1.4219] |
| CACHE_Q1_LEGACY/LIB | 1.3558 [1.2484, 1.4245] |
| FULL_Q1_LEGACY/LIB | 1.3642 [1.2576, 1.4329] |


主 q1 路径不再生成 sideband；合法主链为 pack→up→SiLU→multiply→down→unpack→gate→reduce。可选融合在完整 up kernel 后执行，把 SiLU 和 multiply 合为一个 pointwise kernel，显式保留 SiLU→half 舍入和乘法→half 舍入，不跨 CTA 读取未完成 GEMM 结果。

| 比较：耗时比，小于 1 更快 | 比值 [探索性 95% 区间] |
|---|---|
| Q1_MINIMAL/CACHE_Q1_LEGACY | 0.9996 [0.9969, 1.0036] |
| Q1_MINIMAL_FUSED/CACHE_Q1_LEGACY_FUSED | 0.9972 [0.9956, 0.9989] |
| Q1_MINIMAL_FUSED/Q1_MINIMAL | 0.9933 [0.9918, 0.9963] |
| CACHE_Q1_LEGACY_FUSED/CACHE_Q1_LEGACY | 0.9957 [0.9943, 0.9983] |


融合同时给予同 q CACHE 和 Q1_MINIMAL；这只属于现成算子融合工程。两种输入 ring 层还给予 LIB 相同 activation 融合机会。其余两层没有独立 LIB_FUSED 计时，不能据此作全域同融合生产库优势主张。

本轮 activation 融合平均节约约 0.43%（CACHEq1）和 0.67%（Q1_MINIMAL）的 CPU-ready 层时间，只有三块、四个已知层的探索证据；这是小幅工程收益，不能计为新调度信息收益。

## 输入变化与冷热边界

8 个 activation 槽预先分配，共享同一组权重、相同 counts/route/descriptor 和每策略一个 Graph。每请求的 Python 槽选择与一次 D2D copy 都在 ready/event 时间内；HOT_SLOT0_COPY 同样含一次 copy。资格逐槽完整核对。此模式叫 `DYNAMIC_ACTIVATION_FIXED_DESCRIPTORS`，不是在线 router，也不是动态 counts。

**HOT_SLOT0_COPY（CPU-ready）：**

| 比较：耗时比，小于 1 更快 | 比值 [探索性 95% 区间] |
|---|---|
| Q1_MINIMAL_FUSED/CACHE_Q1_LEGACY_FUSED | 0.9968 [0.9953, 0.9976] |
| Q1_MINIMAL_FUSED/LIB_FUSED | 1.4210 [1.3951, 1.4429] |
| CACHE_Q1_LEGACY_FUSED/LIB_FUSED | 1.4256 [1.3988, 1.4463] |

**ACTIVATION_RING8_FIXED_DESCRIPTORS（CPU-ready）：**

| 比较：耗时比，小于 1 更快 | 比值 [探索性 95% 区间] |
|---|---|
| Q1_MINIMAL_FUSED/CACHE_Q1_LEGACY_FUSED | 0.9958 [0.9932, 0.9972] |
| Q1_MINIMAL_FUSED/LIB_FUSED | 1.4133 [1.3790, 1.4454] |
| CACHE_Q1_LEGACY_FUSED/LIB_FUSED | 1.4192 [1.3884, 1.4495] |


所有正式测量先热身至少 64 次且事件跨度 ≥150 ms。算子重复数由一次 LIB pilot 决定，限制 32–256，所有策略共用；事件跨度含提交空隙，不伪装 GPU busy time 或请求 p99。算子有 1030 个 phase 因 32–256 次边界及不同策略速度而未落在 50–150 ms 目标内，保留实际值，不删样本。层每请求一次输出等待，64 个测量请求不是 64 个独立重复。冷启动、编译、Graph capture、完整动态模型、跨层变权重没有作为生产延迟测量；worker 余量也不是可解释的冷启动成本。

## 数值、日志、统计与预算

- 收集 2010 个 phase、22987 项 phase/层内资格数值摘要（初始 GPU、raw-bit 与 activation 枚举资格另列），失败 0，最大相对 Frobenius 0.00028317796。初始 GPU 资格与一次有限 memcheck 另见 raw worker，CPU 映射小域 1,296 个配置通过。
- 完整输出对 FP64 参考，逐元素 |error|≤0.005+0.005|ref| 且相对 Frobenius≤0.002；同体期望逐位一致。算子 phase 复用字段 `same_body_bitwise` 实际采用 FP16 `torch.equal`（不区分正负零），因此按精确数值相等解释；另用两种固定正式 case × 六个实际 seed 做完整 int16 原始位样本资格。层及 activation 资格使用 int16 检查。见 `VALIDATION_SEMANTICS_NOTE.md`，没有回写日志或放宽容差。
- 统计按每 case/block 配对 log 比值，再等权 case 汇总；20,000 次按进程块 bootstrap。主文所有 95% 区间均探索性；两个同 q 主比较另附 Bonferroni 97.5% 边际区间于 JSON，不把多个图表包装为全域显著。
- 六行 Williams 次序在 6 策略时覆盖位置；5 策略从 10 行设计取预定 6 行，非完整 carryover 平衡。开发 26 策略/3 块、诊断 13 策略/3 块、层主比较 4 策略/6 块、融合 4 格/3 块与 ring 6 项/3 块也不声称完整位置/carryover 平衡。
- 首尾 LIB 锚 150 个 case-block，3 个超过 5%；全部保留，主分母从未替换为有利锚。见 `derived/drift.json` 与 `anchor_sensitivity.json`。
- 采样温度 [63, 78] °C，SM 时钟 [300, 1590] MHz（含准备/空闲）。配置及执行功耗限值见 `summary.json`，100 W 不是锁频；不按温度回归修正速度。
- 新增 worker **0.8937/4 小时**；原累计 **6.3632/16 小时**。旧 92 条账本前缀保持：True；worker 窗口重叠：False。工作墙时单列 `RUN_STATE.json`，不把 CPU 开发/构建排除在 7 小时约束外。
- 全部 raw 数据、不可变 source manifest、实际 Graph DAG、构建/数值/失败记录可由 `RAW_INDEX.json` 追溯；缺项不填零。实际 tensor 未打包，摘要复算不等于在另一机器重新做 GEMM。

## 论文判断与后续边界

目前可带走的是：真正的算子内 grouped 集成、对 q1 映射混淆的明确修正、精简 q1 基线、有限主体/普通 GEMM 分解，以及相同数值语义下的层融合对照。没有证据把这些工程结果称作新的自适应信息方法，也没有进行物理 SM 位置或类 NUMA 干预。正负 case 都保留；局部胜出不替代全域结果。

若同 q 方案没有分开的证据且主体仍落后成熟库，本轮即结束扩展，不改工作集找赢家、不提高 q-budget、不新增 ML/NUMA 实验。进一步工作需新的可证伪机制和独立验证，而不是重新命名现有收益。

5070Ti 交接见 `HANDOFF_5070Ti.md`：可复用协议、同 q 控制和数值合同；T10 的 tile/worker/编译资源/性能数值不能直接迁移。
