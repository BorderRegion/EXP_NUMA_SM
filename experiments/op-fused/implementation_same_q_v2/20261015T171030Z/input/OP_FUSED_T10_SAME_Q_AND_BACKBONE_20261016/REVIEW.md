# 独立审阅：实现完成，但方法效应尚未识别

## 结论

接受本轮为真正的 SM75 Tensor Core 算子内实现与有限对照，不接受“自适应 packet 方法已被正面证明”或“LLM/亲和优化整体失败”。原 `SAME_CORE_GAIN_ONLY / MATH_BACKBONE_GAP` 可以保留，追加 `Q1_MAPPING_CONFOUNDED_WITH_PACKET_POLICY`。

这里没有发现足以认定全部输出错误的源码证据；没有重新执行GPU，不能给出完整正确性保证。主要问题是主张归因和高效基线，不是统计算错。

## 1. 独立核查范围

- 清单1,035项大小和SHA-256全部匹配；ZIP共1,036个成员，另一个为清单自身。
- 从原始JSON重建468个case-block、5,544个phase；其中正式测试288个case-block。
- 独立重算306项case/suite配对效应与20,000次bootstrap，最大数值差约8.9e-16。
- 82,116项正式数值检查摘要均为通过；同体bitwise失败为0。实际tensor未附带，因此这是摘要核查，不是独立重新做矩阵乘法。
- 重算138,240个逐请求时间值的均值（device和ready两列合计），差为0；重建4,608份Graph结构记录。
- 所附SASS中6个数学kernel各64处静态HMMA；未看到这些函数中的静态LDL/STL。不是硬件Tensor Core利用率或实际spill流量证明。
- 数学源码与完整vendor的一致性仍依赖包内报告及pin；本次未下载完整vendor树。未运行.so或GPU程序。

细节见 `evidence/independent_audit.json`、`resource_analysis.json`。

## 2. 真实正负结果

| 范围 | FULL/LIB | FULL/冻结CACHE或同融合S0 | 解释 |
|---|---:|---:|---|
| grouped | 2.0335 | 0.8536 | 比库慢103.35%，比冻结CACHE q4快14.64% |
| dense | 1.5912 | 0.8246 | 同体正效果不等于部署优势 |
| heterogeneous-K | 1.4481 | 0.5812 | 同K/异质K应分开，不叫真实MoE外推 |
| post-route层 | 1.8340 | 0.9098 | 比库慢83.40%，同融合快9.02% |

时间比而非speedup倍数。只有24个固定grouped测试点，不是全部72个。旧结构已看过，不能说全新结构盲测。

局部正例必须保留，例如 grouped-079 与 moe_layer-017；但在moe_layer-017，F0S0与F1S1本来就很接近，不能把相对库的收益全部归给FULL。

## 3. 决定性归因缺口：FULL=q1，CACHE=q4

源位置：`src/packet_visitor.h:55–77,103–115`，`tools/implementation_bench.py:31–57`。

令 `gm=ceil(M/BM)`、`gn=ceil(N/BN)`，当前原生线性tile r对应：

`m=r//gn, n=r%gn`。

packet q=1对应：

`m=r%gm, n=r//gm`。

qcap=1时，各个min约束仍返回1；总tile数、waves和K预算不再影响任务映射。packet_count=gm*gn，within每步立即回0。它与 CACHE q=1 的问题顺序、worker stride、tile覆盖与顺序一致，但 FULL 编译路径仍可能计算无用总量、携带额外变量和分支。

因此当前FULL/CACHE(q4)不是“有/无自适应信息”的纯干预；它同时改变了包长和任务组织。ABL与FULL完全alias，1.0零宽区间只是复用了同一次观测。

用旧开发数据作事后诊断：FULL(r0,q1,w2)/CACHE(r0,q1)=0.99250，探索性95%区间[0.97805,1.00781]。不能据此认定等价性能，但目前没有独立的自适应信息优势。此数据不能回填成新验证集。

同q差异应当实际测一次，不是继续调大q上限强迫出现正例。

补充的源级分类（事后，仅作线索）：4个grouped回归case的所有非空problem都只有一个M tile，q1顺序本来就与CORE相同，FULL/CORE几何均值约1.0074；另20个允许改变M/N遍历顺序的case约0.8773。dense对应3个顺序相同case约1.0335、9个可改变顺序case约0.8260。这个分组不是随机干预，不能据此证明缓存根因，但再次说明普通tile遍历顺序应当是首要基线。见`evidence/order_scope_diagnostic.json`。

## 4. 开发／测试分布差别

完整计划中，24个grouped开发点仅含K=1024/2048和uniform/zipf；测试加入K=4096及one_heavy/sparse_active。全局固定CACHE q4在开发赢、在测试输，本身不是作弊或统计错误，也可能是政策迁移不足。

但是新q规则在K=4096时本就约束q<=1。不能一边将其当多tile复用的目标域，一边在该域从未执行多tile，再宣称目标机制得到验证。

本次所有旧样例现在都是已知回归输入。后续新split要如实标记，不能重命名seed当新程序。

## 5. 高效主体需要更具体的检查

已测资源：

| 配方 | 线程/CTA | blocks/SM上限 | 理论驻留warp上限 | 寄存器/线程 CORE/CACHE/FULL |
|---|---:|---:|---:|---|
| 32×128×32 | 64 | 3 | 6 | 192/194/198 |
| 64×128×32 | 128 | 2 | 8 | 174/176/180 |

Turing官方上限为32个resident warp/SM，故对应18.75%与25%的上限代理。不是achieved occupancy，也不是“occupancy低所以必然慢”的证明。高寄存器与有限resident warp、问题查找、M/N尾块、tile形状和数据流水都可能影响吞吐。不能只看到HMMA就叫“高效数学主体”。

本包有一个方便的归因对照：dense_control-024 与 grouped-092 对应相同K/N/总有效M，FULL都约47ms，而LIB约10ms。这不是独立机制证明，但提示许多损失并非只有多expert调度才出现。优先比较单problem的普通CUTLASS GEMM与grouped count=1，并尝试有限的成熟tile实例，不重写Tensor Core主循环。

## 6. sideband不是已证实的融合突破

源位置：`grouped_backend.cu:121–156`、`implementation_layer.py:20–44`。

F1在有用pack内写两个int32总tile值；合法且没有增加调度kernel。可这次qcap=1时这些值不改变映射，精简q1可以彻底不需要该统计。

FULL的F1/F0=0.9994，[0.9979,1.0004]。它既未建立稳定收益，也不能称为必要生产成本被突破。

同时，层内SiLU、gate乘法仍分开执行。它们可以成为有限的工程融合对照，但不是新的调度算法；全局需要完整gate/up结果时，不能在任意GEMM CTA的epilogue跨CTA读取未完成数据。

## 7. 时间与环境

100W已按报告中的独立授权应用并保留保护；本包遥测只说明采样时上限为100W，不说明所有phase频率相同。保留全部漂移块。旧数据不按温度回归重写。

主grouped一Graph含一个grouped kernel，层四格8个kernel；因此不能继续把两倍库差距全部归结为“外置小调度kernel”。没有新增调度launch是真进展。

静态描述符、固定路由、热数据重放是当前范围。模型／动态router／真正在线counts未实现，必须保持未测，不用已有数千phase替代这些证据。

## 8. 下一阶段建议

用6–7小时预算完成：同q因果闭环、精简q1实现、有限成熟主体适配、同融合层验证。暂不扩attention、不做新NUMA测试、不加载新模型、不重复已完成的大矩阵。

正确性只做必要的3层：CPU映射；小GPU完整输出；正式阶段末和少量样本完整核对。主目标是测明白新增能力和生产差距，不是再写检查器。
