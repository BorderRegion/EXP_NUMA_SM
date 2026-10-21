# T10：算子内调度方案审阅与原生基线实测

**结论状态：IMPLEMENTATION_OR_RESOURCE_LIMITED。核心候选调度尚未完成 GPU 实现，不能据此判定它有效或无效，更不能称为 NUMA 成果。** 本轮在离线约束下完成了能支持的真实 GPU 原生基线、完整 post-route 层及 attention 成本测量；缺项保留在原计划分母中。

另有重要测量条件：机器预先安装的 `t10-quiet-fan.service` 会在 GPU 温度≥80°C（或风扇低转速）时把功耗上限降为100W，在温度≤70°C且转速正常后恢复125W。运行中真实触发了该机制。本任务仅只读检查，没有改功耗、风扇、驱动或保护服务。所有状态混合的汇总只能作描述；每 case 的功耗条件分层和转换区间已附，不能宣称固定功耗下的性能。

![实际温度、频率与功耗条件](figures/thermal_operating_conditions.png)

## 1. 到底完成了什么

原计划216个逻辑case；测到原生基线 156 个，其中 156 个有6个独立进程块，共 936 个 case-block、4248 个测量phase。这里的“完成”只指原生基线覆盖，**候选方法覆盖为0**。资格和后端试编译另计，不混进正式统计。数值通过不等于资源合同全部通过：attention_decode-047的按记录峰值的保守显存余量检查未通过，详见第7节。

| 套件 | 原计划case | 原生基线已测 | 六块完整 | 候选已测 |
|---|---:|---:|---:|---:|
| grouped | 96 | 48 | 48 | 0 |
| dense_control | 24 | 24 | 24 | 0 |
| heterogeneous_k | 12 | 12 | 12 | 0 |
| attention_decode | 48 | 48 | 48 | 0 |
| prefill_control | 12 | 12 | 12 | 0 |
| moe_layer | 24 | 12 | 12 | 0 |

| 层级 | 真实执行范围 | 未达到的范围 |
|---|---|---|
| OP_RESIDENT | cuBLAS/cuBLASLt、原生CUTLASS decode attention、原生MATH prefill | 可修改 Tensor Core grouped visitor 和 FULL |
| PRODUCER_CONSUMER | decode查询布局；GPU长度前缀；16项合成Q/长度序列、3组有用KV输入轮换 | 新scheduler sideband、真实在线trace、动态GEMM路由 |
| LAYER | 全部专家权重驻留的合成MoE post-route层：pack、gate/up、SwiGLU、down、加权combine | router、count/scan、optimized MoE库、候选融合四格、完整attention block |
| MODEL | 本地权重/配置/环境审计 | 没有完整模型请求或生成性能结果；不是随机小模型替代 |

## 2. 主体资格与实现边界

本地两套已安装环境：PyTorch2.8.0+cu128/Triton3.4.0，以及PyTorch2.9.1+cu130/Triton3.5.1。两版本各做两个合法tile配方的有限 SM75 检查，数值能算对，但保存的PTX仅有普通`fma.rn.f32`，没有MMA/WMMA。这不等于证明所有可能实现都不支持T10；它说明本地这条有限适配没有获得本任务要求的成熟Tensor Core主体。没有扩展为手写SIMT新方法。

cuBLAS原生实测符号包含`cutlass_75_wmma_tensorop...`；PyTorch attention实测为`fmha_cutlassF_f16_aligned_32x128_rf_sm75`。已编译库能运行，不意味着本地有可修改的完整CUTLASS依赖。在规定的本地搜索范围里没有完整依赖，也没有FlashInfer/vLLM/SonicMoE/xformers。

直接fused GQA接口拒绝Q32/KV8。decode适配把每个KV头共享的4个查询头排成4个独立查询行，再恢复输出顺序；所有查询仍读原KV，不增造共享，也不改softmax数学。它是一种布局适配，**不是内部scheduler创新**。prefill仅运行原生MATH GQA非causal控制，不将decode适配错误推广过去。

GEMM开发选择只使用24个grouped开发case，排除dense/异质K控制。请求cuBLASLt preference / cuBLAS preference的等case几何时间比为 1.08518，选择冻结为cuBLAS preference。库内部可能回退，未逐shape独立追踪两种库入口，不能把preference标签当成每cell真实库身份的完整证明。这个开发集选择也处在上述保护策略下，不能视为其他功耗/平台的普遍最优。最初混合42点的CPU汇总未用于测试，已保留并说明修正。

## 3. 六策略与融合四格

| 策略 | 状态 | 理由 |
|---|---|---|
| LIB | 原生参考已实测 | 包含逐problem调用和补查发现的原生cublasGemmGroupedBatchedEx；均给Graph条件，实际节点数另录 |
| CORE / BAL / CACHE | NA | 缺可修改且通过Tensor Core资格的数学主体 |
| FULL / ABL | NA | 没有用慢SIMT或外置planner冒充主实现 |
| F0S0 / F1S0 / F0S1 / F1S1 | NA | 没有合格S1和新增F1；Graph并不是kernel fusion |

因此FULL/LIB、FULL/同融合强简单基线、融合交互、调度摊销回本均为null。没有填成0，也没有用“Graph比eager快”替代新方法收益。无需把预算跑满来制造方法结论。

## 4. 已有后端的真实成本

### 补查后的强库基线

本机已安装cuBLAS的`cublasGemmGroupedBatchedEx`实际可用；不能把“没有可改的grouped源码”写成“没有grouped库接口”。该入口使用FP16输入/输出、FP32计算并显式禁止reduced-precision reduction，Graph资格包含同一个Graph在更换输入、输出填NaN后的多次重放检查。它仍是闭源库内部调度，没有实现FULL。

这项补充在原生逐专家实验之后才发现，作为独立cohort保留，不改写原冻结时间线。正式计时前按原生API标准用法将相同(M,N,K)矩阵合为group_size>1，使用稳定首次出现顺序，指针身份保持；重复尺寸、空expert、更换输入和输出填NaN均重新资格。没有看强库性能后再选择分组规则。24个原开发case、24个原先选定的留出case、6个原先选定的留出层case各安排6进程块；开发首块12个case因只读Graph零边查询异常未计时，保留失败、不补跑，因此它们为5个有效块，其余按实际记录。修复只改变审计边界，数学和计时未变，另通过单kernel零边Graph资格。累计实际 312 个case-block、1248 个phase，失败记录 12 条。开发集native-grouped/per-expert几何时间比 1.04026，全局选择冻结为`PER_EXPERT_GRAPH`；开发选择仍对24个case等权，分别采用可用5/6块均值，缺失和修订在`strong_valid_blocks_amendment.json`列明；测试集不选参数。

层对照复用同一组输入、权重、路由、输出和非GEMM步骤，只把两段逐专家GEMM分别换成原生grouped调用。双方Graph，每请求测到输出ready：

| 层case | 独立进程块 | 逐专家Graph ready ms | 原生grouped Graph ready ms | grouped / 逐专家 |
|---|---:|---:|---:|---:|
| moe_layer-007 | 6 | 1.3487 | 1.5301 | 1.1344 |
| moe_layer-008 | 6 | 2.2164 | 2.2322 | 1.0071 |
| moe_layer-009 | 6 | 1.7830 | 2.2465 | 1.2588 |
| moe_layer-016 | 6 | 8.2941 | 8.4165 | 1.0145 |
| moe_layer-017 | 6 | 40.0195 | 34.3800 | 0.8586 |
| moe_layer-024 | 6 | 135.6779 | 137.2850 | 1.0109 |

完整区间、逐块值和功耗条件分层见`strong_library_results.json`。只读CUDA Graph节点检查保存真实kernel名称、grid/block和节点种类，没有为补充基线增加CUPTI采样。库的grouped API数量不等于GPU kernel数量；也不能仅凭函数名宣称每个shape均采用Tensor Core。Graph中可能存在库内辅助kernel，其成本全部包括。

24个留出算子的native-grouped/逐专家Graph几何时间比为 **1.31851**，探索性95%区间 [1.30248, 1.33611]；6个留出层的逐请求ready比为 **1.04013**，区间 [1.02220, 1.05926]。比值大于1表示原生grouped更慢。这是各自6个进程块、既有温控策略下全部已测状态的描述性汇总，不是锁频或固定功耗结论；每个shape的正负例仍全部列出。它支持保留开发时冻结的逐专家Graph参考，不能代替对FULL的检验。

开发首块缺12点，冻结选择使用“24个case各自5/6块均值再等case汇总”。`strong_library_summary.json`的E1进程优先汇总因首块case构成不同，权重与冻结公式不同，只是诊断，不作为该选择公式的置信区间；留出E3/E4的每块case集合完整相同。

![同Graph的强库对照](figures/strong_library_comparison.png)

此补充只适用于固定描述符、热算子/固定post-route层。host尺寸数组和device指针数组在准备阶段建立，未包含逐请求变化路由所需的descriptor重建；不能推断真实动态MoE收益。新旧cohort不跨时间直接相减，所有库比值在同一case-block内配对。

以下是6进程块的算术平均毫秒，包含全部已测保护状态，仅作可用后端成本示例。区间、逐块值、功耗分层在`derived/native_v1/case_results.json`。

| decode case | resident内核 | 布局+内核+还原 | 动态prefix+布局+3组KV | 原生MATH |
|---|---:|---:|---:|---:|
| attention_decode-001 (B=1, L均值=128, uniform) | 0.0089 | 0.0141 | 0.0212 | 0.0857 |
| attention_decode-030 (B=16, L均值=1024, long_tail) | 0.5238 | 0.5331 | 0.5165 | 9.3373 |
| attention_decode-045 (B=32, L均值=4096, uniform) | 7.6321 | 7.6749 | 7.7223 | 149.7436 |

MATH与CUTLASS之间的差异是已有后端/布局执行方式的差异，不能叫新调度收益。动态列同时改变metadata准备和输入/KV工作集，不能从差值直接算纯metadata或cache因果。所有输入来源是SYNTHETIC_MECHANISM；没有真实在线流量。

各shape的有效矩阵收缩FLOPs、active输入/权重/输出逻辑payload、驻留权重和派生吞吐见`logical_work_and_payload.csv`。grouped的逻辑payload排除空expert未访问的权重，但驻留权重仍包含全部expert；attention不把共享KV虚增成Q头份数。这些只是代数工作量/一份张量字节，不是实际DRAM带宽或GPU busy时间；不据此判定compute-bound或memory-bound。

![逐专家cuBLAS的grouped负载成本](figures/grouped_native_heatmap.png)

![attention不同入口成本](figures/attention_native_scopes.png)

![post-route层Graph与eager](figures/layer_native_graph_eager.png)

另补充原六个留出层形状的逐请求边界实验，共 35 个 case-block、140 个phase；每请求只在完整输出可用后同步，保存真实128条时间样本。它仍是合成固定路由、权重驻留并重复使用的post-route层，不是全模型服务延迟。以下为实际CPU ready均值：

| 层case | 独立块 | Graph ready ms | Eager ready ms | 配对Graph/Eager |
|---|---:|---:|---:|---:|
| moe_layer-007 | 6 | 1.3377 | 1.3301 | 1.0058 |
| moe_layer-008 | 6 | 2.2042 | 2.2110 | 0.9970 |
| moe_layer-009 | 6 | 1.7660 | 1.7644 | 1.0008 |
| moe_layer-016 | 6 | 8.2430 | 8.2246 | 1.0023 |
| moe_layer-017 | 6 | 40.0319 | 40.1804 | 0.9963 |
| moe_layer-024 | 5 | 134.7859 | 133.4980 | 1.0095 |

每请求的两个预分配CUDA event记录及端点同步属于测量开销，双方相同；它们没有进入专家内部。区间、功耗分层和raw索引见`layer_request_results.json`/`layer_request_phase_means.csv`。没有把128次请求称为128个独立实验，也不据此承诺p99 SLO。

该Graph/eager逐请求cohort的第0块最大层024被显存预检拒绝，原因是runner的`locals()`缓存保留前一大case的闭包引用。一次局部清理修复后最大层通过，清理后显存恢复；首块失败保留、没有补跑。这不是设备无法容纳该形状的证据。最大层该项只有5个有效块；原批量层和独立强库cohort分别记录。失败解释见`request_runner_repair.json`。

## 5. 方案本身的质疑

1. 预设work_budget来自开发集K的75分位×2，约对应4096个K元素；最大K=4096时q上界=1。该组全部32个case都无法检验多个tile打包的复用收益。q=1不保证访问顺序与原生完全相同，因此也不能简单说“整个方法退化为原生”。CPU枚举只证明规则性质，不是GPU性能。
2. 小token/多expert时很多M不足一个tile，包长本来就可能为1。权重驻留、padding和每problem开销可能比调度信息更重要；不能新增无意义token制造并行度。
3. persistent、同expert/panel分组、K排序和变长attention调度已有近邻。本包给出的文献摘要是来源线索，本轮离线未全文查新；不能称首创。
4. 所有位置相关L2主张均未测试。本轮逻辑复用或GPU占用能力即使未来有增量，也不能自动叫SM间NUMA。
5. 当前机器的温控功耗策略是额外混杂。单看总耗时差、kernel名或温度终值，无法分清参数、缓存、提交、频率和内部调度。

## 6. 正确性、统计及漂移

FP16输入、FP32累加；关闭TF32和FP16 reduced-precision reduction。参考使用分块FP64计算；层参考保持明确的FP16中间写回边界。元素误差满足`abs <= .005 + .005*abs(ref)`，并要求归一化Frobenius≤.002。正式保存 48308 条完整输出检查记录，全部通过为 True；最大归一化Frobenius误差 0.000289244。这不是完整LLM质量保证。

每phase≥64次且≥0.3秒有用热身；测量128–512次，所有同case方法共用重复数。GPU数值是同一context下CUDA event时间跨度，可能包含提交空隙，不是GPU busy time；ready时间按真实批次端点计入CPU提交。未从batch均值虚构p99。全部decode方法统一每Graph包含16个请求并按16摊销，给予各原生入口同样的提交摊销机会。层批量实验同样是摊销吞吐，不能直接当作请求延迟。

独立单位为process/input-sequence block，先在块内形成比值；跨case汇总先在同process块内等权平均，再bootstrap20000次。native比较全部探索性。四策略六块并非完整Williams周期，实际顺序全部保存，不能声称完全消除carryover。两主假设FULL/LIB和FULL/S0没有被检验，所以没有伪造Holm显著性。

具体实施为6个分别启动的进程，输入seed使用`2026101517 + block % 3`，即3组随机输入循环两遍；它不是6组全新独立内容。置信区间描述这组输入和运行策略下的进程块差异，不覆盖未知真实请求分布。输入重复及温控状态相关性限制外推。

20/936 个case-block首尾锚差超过5%，全部保留。主LIB始终位于主序列，不被有利尾锚替换。功耗状态转换及跨状态配对独立标记，不做温度回归“修正”，也不把跨条件平均称稳定收益。

`anchor_and_input_sensitivity.json`另列每个配对采用头锚/尾锚时的区间、方向翻转标记，以及3组重复输入seed的家族均值范围。接近1时的翻转只作DRIFT_LIMITED敏感性提示，不筛掉不利块。`sensitivity_summary.json`披露累计设备测量区间是否落在协议建议50–200ms；GEMM/层/prefill统一128次、decode128–512次的预算选择使部分小算子不足50ms、慢MATH显著超过200ms。实际时长全部保存，不能声称每phase均达到该建议区间。

## 7. 资源、初始化与预算

本轮累计GPU-worker占用 11810.6 秒（3.281小时），授权上限16小时。获锁等待不计并发收益；真实进程窗重叠检查结果：[]。这不是纯GPU busy时间，包含持锁时的导入、JIT资格、初始化、reference和I/O。

| 阶段 | worker秒 |
|---|---:|
| E0 | 42.8 |
| E1 | 875.6 |
| E2 | 0.0 |
| E3 | 2577.2 |
| E4 | 2887.2 |
| E5 | 5427.8 |
| E6 | 0.0 |
| E7 | 0.0 |

最大PyTorch reserved峰值 14.338GiB，case结束时最小可用显存 2.958GiB；这些与1Hz遥测和前后健康查询一并保留，结束时可用显存不是连续最小值。最大MoE配置的全部专家权重真实驻留。没有offload、删专家或静默缩小维度。

显存余量有一个未闭合的资格项：`attention_decode-047`（B32/L均值4096/staggered）的6块均记录到约14.338GiB allocator reserved峰值，超过“runtime total减15%余量”的阈值；同时活跃分配峰值仅约2.853GiB、case结束free约6.57–6.58GiB，进程1Hz NVML采样也明显低于该reserved峰值。现有数据无法确定短瞬间物理用量或解释所有计数差异，不能拿结束时free证明全过程合规。该shape按记录reserved峰值未通过保守余量门槛，标`MEMORY_MARGIN_NOT_QUALIFIED`；数值和计时原样保留，但不得用于声称满足本包严格余量条件的确认性结论；不是OOM或硬件故障的证明。该峰值按整个case记录，不能归因给特定variant、准备或验证阶段；进程同时持有多个基线Graph和高精度参考，也不能据此断言单个生产入口必需这么多显存。预分配估算guard不等于持续强制余量，详见`MEMORY_HEADROOM_AUDIT.json`。未为掩盖它缩形状或补跑。

`initialization_and_reference_s`包含资格reference、分配和Graph capture，不能冒充部署冷启动。Graph capture/JIT的独立摊销没有充分分离，列UNKNOWN；新候选回本为未建立。新资源费用0元；本地电费未计量。没有下载、安装、远程GPU、驱动/时钟/功耗设置变更，也没有重跑旧渲染/CSR实验。

旧时段机器日志另保存于`prior_thermal_events_context_only.json`：2026-10-14和旧补充实验时段也有保护/恢复事件。本轮没有逐phase重新对齐旧实验，因此既不宣称旧比值全部失效，也不改写旧效应量。论文引用旧结果时需要单独审计这个运行条件。

## 8. 本地模型与论文定位

本地确有Qwen3-0.6B文本编码器权重（SHA256见`config/model_asset.json`，存储BF16）和Qwen3.5-4B命名资产。本轮缺已集成候选及已验证FP16全模型数值合同，故不声称完成全模型生成、TTFT/TPOT或质量对比。模型缺项不能填成0收益，也不能说“这台机器没有模型文件”。

当前能交付的是可复算原生基线、合法GQA布局适配的成本边界、协议审阅和后端/温控限制。不能写“提出并验证NUMA调度算法”，也不能写“推理负载证明该方向无效”。下一轮的首要缺口是本地完整且兼容SM75的可修改Tensor Core grouped/attention源码，之后才有资格实施唯一候选、同融合强简单基线和真实模型检验。5070Ti尚未在本机测试，不作正负预测。

## 9. 复核入口

- `PLAN_REVIEW_t10.md`、`LOCAL_RESOURCE_GAPS.md`：方案质疑和缺项。
- `BACKEND_CARD.md`、`IMPLEMENTATION_DELTA.md`：实际调用与未实现部分。
- `KERNEL_DAG_BEFORE_AFTER.md`、`LAUNCH_AND_TRANSFER_LEDGER.csv`、`profile_census.json`：节点与来源。
- `summary_t10.json`、`derived/native_v1/phase_means.csv`、`case_results.json`、`drift.json`：完整标量结果和分层。
- `registry/runs.jsonl`、`runs/*`：源快照、逐块原始数值、资格、时间戳、遥测和失败记录。
- `REPRODUCE.md`：从原始标量复算；再次GPU运行须另建campaign，不能覆盖现有块。

轻量包不含模型权重、巨大tensor、安装库、JIT缓存或GPU二进制。输入由固定seed和源码重建；保存的是实际测量与完整数值比较摘要，不声称打包了全部输入输出tensor。
