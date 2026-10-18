import collections,csv,json,pathlib,datetime
ROOT=pathlib.Path(__file__).resolve().parents[1]
R=ROOT/'reports';D=ROOT/'derived/native_v1'
def write(name,text):(R/name).write_text(text,encoding='utf-8')
def main():
 s=json.loads((D/'summary_t10.json').read_text());cases=json.loads((D/'case_results.json').read_text());lookup={x['case']['case_id']:x for x in cases}
 assert s['campaign_execution_complete'],'Final report requires the finite campaign to finish.'
 reg=[json.loads(x) for x in (ROOT/'registry/runs.jsonl').read_text().splitlines()]
 lib=json.loads((ROOT/'preregistration/library_freeze.json').read_text())
 strong=json.loads((D/'strong_library_results.json').read_text())
 strong_summary=json.loads((D/'strong_library_summary.json').read_text())
 strong_freeze=json.loads((ROOT/'preregistration/strong_library_freeze.json').read_text())
 group_test=strong_summary['aggregate_descriptive_mixed_conditions']['E3']['device']
 layer_test=strong_summary['aggregate_descriptive_mixed_conditions']['E4']['ready']
 strong_table='\n'.join(f"| {x['case_id']} | {x['blocks']} | {x['variants']['PER_EXPERT_GRAPH']['ready']['mean_ms']:.4f} | {x['variants']['NATIVE_GROUPED_GRAPH']['ready']['mean_ms']:.4f} | {x['native_over_per_expert']['ready']['ratio']:.4f} |" for x in strong if x['stage']=='E4')
 coverage='\n'.join(f"| {name} | {x['planned']} | {x['baseline_measured']} | {x['complete_six_blocks']} | 0 |" for name,x in s['coverage_by_suite'].items())
 examples=[]
 for ident in ['attention_decode-001','attention_decode-030','attention_decode-045']:
  x=lookup[ident];v=x['variants'];c=x['case']
  if not v:continue
  examples.append(f"| {ident} (B={c['batch']}, L均值={c['mean_kv']}, {c['distribution']}) | "+' | '.join(f"{v[k]['mean_ms']:.4f}" for k in ['CUTLASS_RESIDENT','CUTLASS_READY','CUTLASS_DYNAMIC16','MATH_READY'])+' |')
 stages='\n'.join(f"| E{i} | {s['worker_by_stage'].get('E'+str(i),0):.1f} |" for i in range(8))
 requests=json.loads((D/'layer_request_results.json').read_text())
 request_table='\n'.join(f"| {x['case_id']} | {x['blocks']} | {x['variants']['CUBLAS_GRAPH_REQUEST']['mean_ready_ms']:.4f} | {x['variants']['CUBLAS_EAGER_REQUEST']['mean_ready_ms']:.4f} | {x['graph_over_eager_ready']['ratio']:.4f} |" for x in requests)
 records=[];profiles=[];peak=0;minfree=None;checks=[]
 for m in reg:
  for p in (ROOT/m['path']).glob('*.json'):
   x=json.loads(p.read_text())
   if 'case' not in x or x.get('status') not in ('BASELINE_ONLY','BASELINE_REQUEST_LATENCY_ONLY','STRONG_LIBRARY_BASELINE_ONLY'):continue
   if '_native_block_' not in m['key'] and not m['key'].startswith('E4_request_block_') and '_strong_block_' not in m['key']:continue
   peak=max(peak,x['peak_reserved_bytes']);minfree=min(minfree,x['free_bytes_after']) if minfree is not None else x['free_bytes_after']
   trace=p.parent/(x['case']['case_id']+'_trace.json');counts=None
   if trace.exists():
    es=json.loads(trace.read_text())['traceEvents'];cc=collections.Counter(e.get('cat','') for e in es);counts=dict(kernel=cc['kernel'],memset=cc['gpu_memset'],memcpy=cc['gpu_memcpy'])
    profiles.append(dict(case_id=x['case']['case_id'],run_id=m['run_id'],variant=x.get('observed_profile_variant',x['phases'][0]['variant']),requests=x.get('observed_profile_requests',1),counts=counts,source=str(trace.relative_to(ROOT)),kernels=[dict(name=e['name'],duration_us=e.get('dur'),args=e.get('args')) for e in es if e.get('cat')=='kernel']))
   ledger=x['ledger']
   for y in x['phases']:
    checks.extend(y['correctness'])
    if y['phase_role']!='primary':continue
    observed=counts if counts and y['variant']==x.get('observed_profile_variant',x['phases'][0]['variant']) else None
    graph_source=False
    if y['variant'] in x.get('graph_structure',{}):
     def flatten(ns):return [n for node in ns for n in [node,*flatten(node.get('children',[]))]]
     ns=flatten(x['graph_structure'][y['variant']]['nodes']);observed=dict(kernel=sum(n['type']==0 for n in ns),memset=sum(n['type']==2 for n in ns));graph_source=True
    unit=x.get('observed_profile_requests',1)
    native_group=y['variant']=='NATIVE_GROUPED_GRAPH'
    records.append(dict(case_id=x['case']['case_id'],block=x['block'],backend='cublasGemmGroupedBatchedEx' if native_group else ledger['backend'],scope=y.get('scope',x.get('scope','LAYER_POST_ROUTE_REQUEST_FIXED_COUNTS')),variant=y['variant'],mode=y.get('mode','GRAPH' if 'GRAPH' in y['variant'] else 'EAGER'),kernel_nodes=observed['kernel']/unit if observed else None,memset_nodes=observed['memset']/unit if observed else None,H2D_bytes=None if graph_source and any(n['type']==1 for n in ns) else ledger.get('H2D_bytes'),D2H_bytes=None if graph_source and any(n['type']==1 for n in ns) else ledger.get('D2H_bytes'),metadata_bytes=ledger.get('metadata_bytes',0)+(24*ledger.get('gemm_api_calls',0) if native_group else 0),extra_plan_launches=0,host_waits_inside_production=0,host_waits_at_request_boundary=1 if x['status']=='BASELINE_REQUEST_LATENCY_ONLY' or x.get('scope')=='POST_ROUTE_FIXED_COUNTS_TRUE_REQUEST_READY' else 0,explicit_wrapper_plan_calls=0,capture_count=1 if y.get('mode','GRAPH' if 'GRAPH' in y['variant'] else 'EAGER')=='GRAPH' else 0,graph_replay_requests=y.get('unit_requests',1),gemm_construction_api_calls=x['native_grouped_ledger']['gemm_api_calls'] if native_group else ledger.get('gemm_api_calls'),pointwise_pack_combine_api_calls=ledger.get('pointwise_pack_combine_api_calls'),source='CUDA_GRAPH_INTROSPECTION_AND_HOST_WRAPPER' if graph_source else ('CUPTI_TRACE_AND_HOST_WRAPPER' if observed else 'HOST_WRAPPER_INTERNAL_NODE_COUNT_UNKNOWN'),raw_ref=str(p.relative_to(ROOT))))
 with (R/'LAUNCH_AND_TRANSFER_LEDGER.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
 (R/'profile_census.json').write_text(json.dumps(profiles,indent=2))
 numeric=dict(check_records=len(checks),all_pass=all(x['pass'] for x in checks),max_abs=max(x['max_abs'] for x in checks),max_relative_frobenius=max(x['relative_frobenius'] for x in checks),peak_reserved_bytes=peak,min_case_end_free_bytes=minfree,warning='Maximum absolute error is not alone the criterion: elementwise atol+rtol and relative Frobenius are jointly tested. Free-at-end is not a continuous minimum; peak reserved and 1Hz telemetry also retained.')
 (R/'numerical_and_memory_summary.json').write_text(json.dumps(numeric,indent=2))
 write('OPERATOR_FUSED_SCHEDULING_REPORT_t10.md',f'''# T10：算子内调度方案审阅与原生基线实测

**结论状态：IMPLEMENTATION_OR_RESOURCE_LIMITED。核心候选调度尚未完成 GPU 实现，不能据此判定它有效或无效，更不能称为 NUMA 成果。** 本轮在离线约束下完成了能支持的真实 GPU 原生基线、完整 post-route 层及 attention 成本测量；缺项保留在原计划分母中。

另有重要测量条件：机器预先安装的 `t10-quiet-fan.service` 会在 GPU 温度≥80°C（或风扇低转速）时把功耗上限降为100W，在温度≤70°C且转速正常后恢复125W。运行中真实触发了该机制。本任务仅只读检查，没有改功耗、风扇、驱动或保护服务。所有状态混合的汇总只能作描述；每 case 的功耗条件分层和转换区间已附，不能宣称固定功耗下的性能。

![实际温度、频率与功耗条件](figures/thermal_operating_conditions.png)

## 1. 到底完成了什么

原计划216个逻辑case；测到原生基线 {s['baseline_cases']} 个，其中 {s['complete_six_block_cases']} 个有6个独立进程块，共 {s['formal_case_blocks']} 个 case-block、{s['formal_phases']} 个测量phase。这里的“完成”只指原生基线覆盖，**候选方法覆盖为0**。资格和后端试编译另计，不混进正式统计。数值通过不等于资源合同全部通过：attention_decode-047的按记录峰值的保守显存余量检查未通过，详见第7节。

| 套件 | 原计划case | 原生基线已测 | 六块完整 | 候选已测 |
|---|---:|---:|---:|---:|
{coverage}

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

GEMM开发选择只使用24个grouped开发case，排除dense/异质K控制。请求cuBLASLt preference / cuBLAS preference的等case几何时间比为 {lib['cublaslt_over_cublas']:.5f}，选择冻结为cuBLAS preference。库内部可能回退，未逐shape独立追踪两种库入口，不能把preference标签当成每cell真实库身份的完整证明。这个开发集选择也处在上述保护策略下，不能视为其他功耗/平台的普遍最优。最初混合42点的CPU汇总未用于测试，已保留并说明修正。

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

这项补充在原生逐专家实验之后才发现，作为独立cohort保留，不改写原冻结时间线。正式计时前按原生API标准用法将相同(M,N,K)矩阵合为group_size>1，使用稳定首次出现顺序，指针身份保持；重复尺寸、空expert、更换输入和输出填NaN均重新资格。没有看强库性能后再选择分组规则。24个原开发case、24个原先选定的留出case、6个原先选定的留出层case各安排6进程块；开发首块12个case因只读Graph零边查询异常未计时，保留失败、不补跑，因此它们为5个有效块，其余按实际记录。修复只改变审计边界，数学和计时未变，另通过单kernel零边Graph资格。累计实际 {strong_summary['case_blocks']} 个case-block、{strong_summary['phases']} 个phase，失败记录 {strong_summary['failure_records']} 条。开发集native-grouped/per-expert几何时间比 {strong_freeze['native_over_per_expert']:.5f}，全局选择冻结为`{strong_freeze['selected']}`；开发选择仍对24个case等权，分别采用可用5/6块均值，缺失和修订在`strong_valid_blocks_amendment.json`列明；测试集不选参数。

层对照复用同一组输入、权重、路由、输出和非GEMM步骤，只把两段逐专家GEMM分别换成原生grouped调用。双方Graph，每请求测到输出ready：

| 层case | 独立进程块 | 逐专家Graph ready ms | 原生grouped Graph ready ms | grouped / 逐专家 |
|---|---:|---:|---:|---:|
{strong_table}

完整区间、逐块值和功耗条件分层见`strong_library_results.json`。只读CUDA Graph节点检查保存真实kernel名称、grid/block和节点种类，没有为补充基线增加CUPTI采样。库的grouped API数量不等于GPU kernel数量；也不能仅凭函数名宣称每个shape均采用Tensor Core。Graph中可能存在库内辅助kernel，其成本全部包括。

24个留出算子的native-grouped/逐专家Graph几何时间比为 **{group_test['ratio']:.5f}**，探索性95%区间 [{group_test['ci95'][0]:.5f}, {group_test['ci95'][1]:.5f}]；6个留出层的逐请求ready比为 **{layer_test['ratio']:.5f}**，区间 [{layer_test['ci95'][0]:.5f}, {layer_test['ci95'][1]:.5f}]。比值大于1表示原生grouped更慢。这是各自6个进程块、既有温控策略下全部已测状态的描述性汇总，不是锁频或固定功耗结论；每个shape的正负例仍全部列出。它支持保留开发时冻结的逐专家Graph参考，不能代替对FULL的检验。

开发首块缺12点，冻结选择使用“24个case各自5/6块均值再等case汇总”。`strong_library_summary.json`的E1进程优先汇总因首块case构成不同，权重与冻结公式不同，只是诊断，不作为该选择公式的置信区间；留出E3/E4的每块case集合完整相同。

![同Graph的强库对照](figures/strong_library_comparison.png)

此补充只适用于固定描述符、热算子/固定post-route层。host尺寸数组和device指针数组在准备阶段建立，未包含逐请求变化路由所需的descriptor重建；不能推断真实动态MoE收益。新旧cohort不跨时间直接相减，所有库比值在同一case-block内配对。

以下是6进程块的算术平均毫秒，包含全部已测保护状态，仅作可用后端成本示例。区间、逐块值、功耗分层在`derived/native_v1/case_results.json`。

| decode case | resident内核 | 布局+内核+还原 | 动态prefix+布局+3组KV | 原生MATH |
|---|---:|---:|---:|---:|
{chr(10).join(examples)}

MATH与CUTLASS之间的差异是已有后端/布局执行方式的差异，不能叫新调度收益。动态列同时改变metadata准备和输入/KV工作集，不能从差值直接算纯metadata或cache因果。所有输入来源是SYNTHETIC_MECHANISM；没有真实在线流量。

各shape的有效矩阵收缩FLOPs、active输入/权重/输出逻辑payload、驻留权重和派生吞吐见`logical_work_and_payload.csv`。grouped的逻辑payload排除空expert未访问的权重，但驻留权重仍包含全部expert；attention不把共享KV虚增成Q头份数。这些只是代数工作量/一份张量字节，不是实际DRAM带宽或GPU busy时间；不据此判定compute-bound或memory-bound。

![逐专家cuBLAS的grouped负载成本](figures/grouped_native_heatmap.png)

![attention不同入口成本](figures/attention_native_scopes.png)

![post-route层Graph与eager](figures/layer_native_graph_eager.png)

另补充原六个留出层形状的逐请求边界实验，共 {s['layer_request_case_blocks']} 个 case-block、{s['layer_request_phases']} 个phase；每请求只在完整输出可用后同步，保存真实128条时间样本。它仍是合成固定路由、权重驻留并重复使用的post-route层，不是全模型服务延迟。以下为实际CPU ready均值：

| 层case | 独立块 | Graph ready ms | Eager ready ms | 配对Graph/Eager |
|---|---:|---:|---:|---:|
{request_table}

每请求的两个预分配CUDA event记录及端点同步属于测量开销，双方相同；它们没有进入专家内部。区间、功耗分层和raw索引见`layer_request_results.json`/`layer_request_phase_means.csv`。没有把128次请求称为128个独立实验，也不据此承诺p99 SLO。

该Graph/eager逐请求cohort的第0块最大层024被显存预检拒绝，原因是runner的`locals()`缓存保留前一大case的闭包引用。一次局部清理修复后最大层通过，清理后显存恢复；首块失败保留、没有补跑。这不是设备无法容纳该形状的证据。最大层该项只有5个有效块；原批量层和独立强库cohort分别记录。失败解释见`request_runner_repair.json`。

## 5. 方案本身的质疑

1. 预设work_budget来自开发集K的75分位×2，约对应4096个K元素；最大K=4096时q上界=1。该组全部32个case都无法检验多个tile打包的复用收益。q=1不保证访问顺序与原生完全相同，因此也不能简单说“整个方法退化为原生”。CPU枚举只证明规则性质，不是GPU性能。
2. 小token/多expert时很多M不足一个tile，包长本来就可能为1。权重驻留、padding和每problem开销可能比调度信息更重要；不能新增无意义token制造并行度。
3. persistent、同expert/panel分组、K排序和变长attention调度已有近邻。本包给出的文献摘要是来源线索，本轮离线未全文查新；不能称首创。
4. 所有位置相关L2主张均未测试。本轮逻辑复用或GPU占用能力即使未来有增量，也不能自动叫SM间NUMA。
5. 当前机器的温控功耗策略是额外混杂。单看总耗时差、kernel名或温度终值，无法分清参数、缓存、提交、频率和内部调度。

## 6. 正确性、统计及漂移

FP16输入、FP32累加；关闭TF32和FP16 reduced-precision reduction。参考使用分块FP64计算；层参考保持明确的FP16中间写回边界。元素误差满足`abs <= .005 + .005*abs(ref)`，并要求归一化Frobenius≤.002。正式保存 {numeric['check_records']} 条完整输出检查记录，全部通过为 {numeric['all_pass']}；最大归一化Frobenius误差 {numeric['max_relative_frobenius']:.6g}。这不是完整LLM质量保证。

每phase≥64次且≥0.3秒有用热身；测量128–512次，所有同case方法共用重复数。GPU数值是同一context下CUDA event时间跨度，可能包含提交空隙，不是GPU busy time；ready时间按真实批次端点计入CPU提交。未从batch均值虚构p99。全部decode方法统一每Graph包含16个请求并按16摊销，给予各原生入口同样的提交摊销机会。层批量实验同样是摊销吞吐，不能直接当作请求延迟。

独立单位为process/input-sequence block，先在块内形成比值；跨case汇总先在同process块内等权平均，再bootstrap20000次。native比较全部探索性。四策略六块并非完整Williams周期，实际顺序全部保存，不能声称完全消除carryover。两主假设FULL/LIB和FULL/S0没有被检验，所以没有伪造Holm显著性。

具体实施为6个分别启动的进程，输入seed使用`2026101517 + block % 3`，即3组随机输入循环两遍；它不是6组全新独立内容。置信区间描述这组输入和运行策略下的进程块差异，不覆盖未知真实请求分布。输入重复及温控状态相关性限制外推。

{s['drift_blocks_over5']}/{s['drift_blocks_total']} 个case-block首尾锚差超过5%，全部保留。主LIB始终位于主序列，不被有利尾锚替换。功耗状态转换及跨状态配对独立标记，不做温度回归“修正”，也不把跨条件平均称稳定收益。

`anchor_and_input_sensitivity.json`另列每个配对采用头锚/尾锚时的区间、方向翻转标记，以及3组重复输入seed的家族均值范围。接近1时的翻转只作DRIFT_LIMITED敏感性提示，不筛掉不利块。`sensitivity_summary.json`披露累计设备测量区间是否落在协议建议50–200ms；GEMM/层/prefill统一128次、decode128–512次的预算选择使部分小算子不足50ms、慢MATH显著超过200ms。实际时长全部保存，不能声称每phase均达到该建议区间。

## 7. 资源、初始化与预算

本轮累计GPU-worker占用 {s['worker_occupied_s']:.1f} 秒（{s['worker_occupied_s']/3600:.3f}小时），授权上限16小时。获锁等待不计并发收益；真实进程窗重叠检查结果：{s['overlapping_gpu_process_windows']}。这不是纯GPU busy时间，包含持锁时的导入、JIT资格、初始化、reference和I/O。

| 阶段 | worker秒 |
|---|---:|
{stages}

最大PyTorch reserved峰值 {peak/2**30:.3f}GiB，case结束时最小可用显存 {minfree/2**30:.3f}GiB；这些与1Hz遥测和前后健康查询一并保留，结束时可用显存不是连续最小值。最大MoE配置的全部专家权重真实驻留。没有offload、删专家或静默缩小维度。

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
''')
 write('CONTRIBUTION_CARD.md','''# 贡献卡

待证命题：成熟算子内有界复用包和尾部约束能否超出同融合、同Graph普通调度？

本轮答案：尚未检验；FULL没有合格GPU实现。

最近方法：包内S1 CUTLASS grouped scheduler、S2 persistent cache-aware grouped GEMM、S4 FlashInfer；本轮离线未全文查新。

实际新增：可复核T10原生基线、decode GQA布局适配与准备成本、动态合成输入/KV ring、温控功耗策略记录、方案退化区间审查。

不能主张：新调度算法优于库、物理NUMA亲和、固定功耗硬件结论、完整模型收益、跨GPU泛化。

下一步所需：完整本地可修改SM75 Tensor Core主体及依赖、同融合强基线、当前GPU动态metadata接入、合格FP16模型合同与独立真实trace。
''')
 write('KERNEL_DAG_BEFORE_AFTER.md','''# 实际DAG与候选缺项

没有实现FULL，因此没有可声称成功的候选before/after DAG。

## Native grouped参考

`resident A/B/shape -> [每个非空problem一次cuBLAS/cuBLASLt调用] -> resident C`

Eager由CPU依次异步提交，不逐expert等待。Graph把同一组调用预录后重放；仍是多个GPU节点，不是一个grouped kernel。

## Native composed MoE层

`外部冻结route/token对 + GPU X -> index_select pack -> 每expert gate/up GEMM -> silu -> multiply -> 每expert down GEMM -> index_select unpermute -> gate multiply -> top-k sum -> output`

全部专家权重驻留，gate/up列在同一矩阵但SwiGLU仍有合法独立边界。不包括router、count/scan；保持原token-expert身份和combine顺序。

## Native decode attention

Resident：`packed Q + packed K/V + cu_seqlens -> fmha_cutlassF_*_sm75 -> packed output`。

Ready：`original Q -> layout copy -> native FMHA -> output layout copy -> ready`。

Dynamic16：每项`device lengths -> zeros/cumsum/cat prefix`，与`current Q -> layout copy`依赖就绪后调用同一native FMHA，再还原输出。16项Q/长度输入和3组独立有用KV输入轮换；没有CPU读取当前长度。prefix是baseline准备成本，不是本轮新scheduler。

数学softmax主体和原生segment/merge不修改；没有跨CTA自旋，没有Green Context。原生cohort的kernel数量以有限CUPTI trace为准；其余API台账明确为HOST_WRAPPER，内部节点UNKNOWN。独立强库cohort每case保存只读CUDA Graph节点结构、kernel名称和grid/block，以GRAPH_INTROSPECTION标注来源。Graph不自动消除节点或中间流量。

## 补查后的原生grouped强库

`resident A/B + host静态尺寸 + device指针数组 -> cublasGemmGroupedBatchedEx -> resident C`

层级对照把原DAG的两段逐expert GEMM各换成一次grouped API调用，其余pack、激活和combine共用相同buffer与操作。描述符预建在timing外，仅适用固定shape/route。库内真正GPU节点数以逐case Graph记录为准，不将1次API调用写成1个kernel。
''')
 write('REPRODUCE.md','''# 复核与复算

当前项目原始数据保留在本机 `op-fused/runs/`。本包带标量raw、源快照、有限trace、固定输入seed、协议和分析源码；不带实际tensor/库/权重。

在本机项目目录执行（解压包可将`op-fused/tools/`替换为包内`tools/`）：

```bash
python3 op-fused/tools/analyze_native.py
python3 op-fused/tools/analyze_strong.py
python3 op-fused/tools/audit_memory.py
python3 op-fused/tools/analyze_sensitivity.py
python3 op-fused/tools/derive_costs.py
python3 op-fused/tools/plot_native.py
python3 op-fused/tools/plot_thermal.py
python3 op-fused/tools/write_report.py
```

默认analyze_native使用已保存 thermal_controller_events.json，离线包可以直接复算；只有原机明确加 --refresh-controller-journal 才读取服务journal。不能用别的机器journal替换。包内phase_means.csv已带重建功耗标签，case_results.json已有功耗分层。

原始进程、顺序、重复数、输入seed、库选择、协议hash见manifest/phase记录。测量源变更只涉及记录、资源异常分类及正式前动态KV ring/重复数冻结；具体版本快照保留。未运行候选，不能用分析脚本生成候选效应。

再次做GPU实验须创建新的campaign/run命名；现有成功或失败块不可覆盖。没有下载/安装步骤。旧实验数据没有迁移进新矩阵。
''')
 write('MENTOR_BRIEF_zh.md',f'''# 导师简报

本轮完成 {s['baseline_cases']} 个原生基线case的六块测量（完整六块 {s['complete_six_block_cases']} 个），不是新算法验证。T10上的cuBLAS和原生CUTLASS attention可运行；两个已安装Triton版本的有限SM75配方只生成SIMT，本地缺可改的完整Tensor Core grouped源码，故FULL、强同体对照与融合四格均NA。

关键质疑：预设work_budget使K=4096的全部32个case包长只能1；小token也常没有可打包tile。布局转换/动态metadata必须计费。机器既有温控服务真实切换125/100W，时延不能跨状态直接归因于调度。

目前可以写资源与实现边界、已有后端成本和测量局限；不能写NUMA成功或推理方向NO-GO。下一步先补齐本地成熟可修改主体，再测唯一候选、同融合强简单基线及真实trace。详见主报告和完整raw索引。
''')
 print(R/'OPERATOR_FUSED_SCHEDULING_REPORT_t10.md')
if __name__=='__main__':main()
