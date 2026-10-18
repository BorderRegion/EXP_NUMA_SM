from runlib import ROOT,sha,utc
import csv,json,collections,statistics,math
D=ROOT/'derived/t10_supplement';P=ROOT/'preregistration/supplement';R=ROOT/'reports';load=lambda p:json.loads(p.read_text())
s1=load(D/'S1_statistics.json');s3=load(D/'S3_statistics.json');b1=load(D/'S1_blocks.json');b3=load(D/'S3_blocks.json');all_probe=load(D/'S2_confirm_summary.json');probe=[p for p in all_probe if p['task_order_randomized']];dev=load(D/'S2_dev_summary.json');gate=load(D/'S4_gate.json');choice=load(P/'S2_layout_choice.json')
if gate['any_pass']:raise SystemExit('S4 gate passed: finish authorized conditional work before final report')
idx=[json.loads(x) for x in (ROOT/'run_index.jsonl').read_text().splitlines()];runs=[r for r in idx if r.get('config',{}).get('campaign')=='T10_ADDENDUM_20261015'];counts=collections.Counter((r['stage'],r['status']) for r in runs);worker=sum(r['worker_seconds'] for r in runs)
assert len([r for r in runs if r['stage']=='S1' and r['status']=='SUCCESS'])==24
assert len([r for r in runs if r['stage']=='S2' and r['status']=='SUCCESS'])==6
assert len([r for r in runs if r['stage']=='S3' and r['status']=='SUCCESS'])==24
# A conservative anchor sensitivity flag does not erase data.
flips={w:(s1[w+'_M/N_head']['ratio']-1)*(s1[w+'_M/N_tail']['ratio']-1)<0 for w in ['W1','W2']}
capacity='NEW_DEPLOYABLE_EFFECT_REQUIRES_REVIEW' if any(s1[w+'_M/N']['ratio_ci97_5'][1]<1 and s1[w+'_M/R']['ratio_ci97_5'][1]<1 for w in ['W1','W2']) else 'MEASUREMENT_CONTEXT_LIMITED' if any(flips.values()) else 'CAPACITY_RESULT_CONFIRMED'
matched=[]
for condition in gate['conditions']:
 if all(s3[condition+'_A/'+ref]['ratio_ci98_75'][1]<1 for ref in ['I','P0','P1']):matched.append(condition)
affinity='CAUSAL_AFFINITY_NO_NET_GAIN' if matched else 'AFFINITY_NOT_ESTABLISHED_IN_SCOPE'
old_prefix=(ROOT/'exports/T10_GPT_轻量包_20261015/run_index.jsonl').read_bytes();assert (ROOT/'run_index.jsonl').read_bytes().startswith(old_prefix)
fixed=load(P/'execution.json')['old_plan_hashes'];assert all(sha(ROOT/p)==h for p,h in fixed.items())
tele=[]
for r in runs:
 f=ROOT/r['path']/'telemetry.csv'
 if f.exists():
  for row in csv.DictReader(open(f)):
   try:tele.append({k.strip():v.strip() for k,v in row.items() if k is not None})
   except Exception:pass
ranges={}
for field in ['temperature.gpu','clocks.current.sm [MHz]','power.draw [W]','utilization.gpu [%]']:
 vals=[]
 for row in tele:
  try:vals.append(float(row[field].split()[0]))
  except (KeyError,ValueError):pass
 ranges[field]=[min(vals),max(vals)] if vals else None
initial=[]
for r in runs:
 if r['stage']=='S3' and r['status']=='SUCCESS':initial.append(dict(run_id=r['run_id'],input=f"{r['config']['bytes']//1048576}MiB/{'irregular' if r['config']['irregular'] else 'coalesced'}",block=r['config']['block'],**load(ROOT/r['path']/'initialization.json')))
(D/'S3_initialization.json').write_text(json.dumps(initial,indent=2));regionmin=min(s['minimum_region_sm_coverage'] for s in probe);smmin=min(s['sm_coverage'] for s in probe)
summary=dict(created_at=utc(),campaign='T10_ADDENDUM_20261015',parent_original_statistic=load(ROOT/'derived/t10/application_statistics.json'),capacity_state=capacity,address_state=affinity,original_state='TOPOLOGY_OBSERVED_NO_DEPLOYABLE_GAIN',paper_position='No established publishable new method on T10; bounded measured evidence, novelty and cross-device generality not established',planned_matrix=dict(S1_blocks=24,S1_sessions=120,S2_allocations=6,S2_configurations=72,S2_rounds=432,S3_blocks=24,S3_sessions=144),actual_counts=[dict(stage=k[0],status=k[1],processes=v) for k,v in sorted(counts.items())],not_executed=dict(S4_snapshot='S3 deployment gate did not pass',S4_dynamic='Snapshot and stable scene-rule prerequisites not reached',physical_memory_mapping='No physical page/L2 partition mapping or physical GPC proof',hardware_cache_hit_counters='Not collected; ordinary/.cg and footprint do not prove service level',RTX5070Ti='Not accessed on this host'),budget=dict(worker_seconds=worker,cap_seconds=21600,old_worker_seconds=load(P/'execution.json')['old_worker_seconds'],actual_rental_cost_CNY=0,electricity='unmetered'),source_refs=['src/supplement/address_kernels.cu','src/supplement/address_probe_runner.cpp','src/supplement/address_deploy_runner.cpp','src/supplement/renderer_runner.cpp','src/supplement/sparse_runner.cpp','tools/runlib.py'],S1_statistics=s1,S3_statistics=s3,S2_layout=choice,S2_confirmation_all=all_probe,S2_confirmation_order_controlled=probe,S2_deviation='Initial3 development and first confirmation used fixed CTA order; only final2 confirmation allocations use fixed per-round shuffle. All72 formal configurations retained; no replacement run beyond cap.',S4_gate=gate,S3_effect_scope='Within-executor empirical table matching only; not established physical address affinity. Per-condition multiple-comparison intervals, not global familywise inference over all4 conditions.',final_checks=load(ROOT/'environment/supplement_final_checks.json'),telemetry_ranges=ranges,old_index_prefix_unchanged=True,old_M_R_hashes_unchanged=True,process_refs=[dict(run_id=r['run_id'],path=r['path'],stage=r['stage'],status=r['status']) for r in runs])
line_patterns={'src/supplement/address_kernels.cu':['read_word(', 'address_probe(', 'address_work('], 'src/supplement/address_probe_runner.cpp':['task_permutation(ctas)', 'chain segment not continued'], 'src/supplement/address_deploy_runner.cpp':['Task-level crossed calibration', 'auto plan_start=', 'Independent placement pass'], 'src/supplement/renderer_runner.cpp':['if(ec_full){ec_launch_mapped', 'conditioning='], 'src/supplement/sparse_runner.cpp':["else if(policy=='E')", 'conditioning='], 'tools/runlib.py':['fcntl.flock', 'process_started_at']}
summary['source_line_refs']=[dict(path=path,line=next(i for i,line in enumerate((ROOT/path).read_text().splitlines(),1) if pattern in line),purpose=pattern) for path,patterns in line_patterns.items() for pattern in patterns]
(R/'T10_SUPPLEMENT.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False))
def ratio(v):return f"{v['ratio']:.4f} [{v['ratio_ci95'][0]:.4f}, {v['ratio_ci95'][1]:.4f}]"
s=f'''# T10 补充实验与论文定位

完成时间：{utc()}。本报告独立于原 E0–E4；旧 CSV、固定 M/R 表和旧统计未修改。比值均为时间比，低于 1 才是更快；区间未特别说明时为 20,000 次进程块配对 bootstrap 的 95% 描述区间，seed=2026101503。W1/W2不池化为跨程序部署结论。

## 结论

计算主线：**{capacity}**。地址支线：**{affinity}**。本轮没有满足既定 S4 部署门槛，因此不进入新的渲染快照或动态场景实验。旧 M 没有因这次补充被重新训练或改表；旧最终状态保留，限于当前静态容量方案和当前执行条件。

状态中的 CAUSAL_AFFINITY 只指“在本执行器内受控换表观察到的经验匹配作用”，**不代表已确认SM到物理内存的亲和因果机制**。局部的缓存、任务顺序和执行组织解释仍然成立。

这是对“原负载是否错过 SM—地址差异”的有界实测回答：原 K2 确实未检验这件事；本轮增加了同地址跨实际 Green 组/SM 的依赖链与吞吐测量，并实际部署了一张初始化匹配表。是否存在可重复局部相关，与它能否产生完整成本收益分别报告。不能从这里证明 T10 不存在 NUMA，也不能把公开组命名为物理 GPC 或显存域。

## 1. 完成范围与记录

S0只读复核完成；S1共24个新进程块、120个session，每个512帧/请求（61,440条）；S2共6个独立进程/分配、72个配置、432个固定轮次；S3共24块、144个phase、每phase128个epoch（18,432条）。前3个S2分配开发，后3个原定确认；其中首个确认在顺序修正前完成，仅作有混杂的初始证据，最后2个确认才有轮换控制。开发轮次在两种窗口布局间分配，未扩成额外配置矩阵。资格与sanitizer单列，不混入正式统计。

补充 worker 总计 **{worker:.3f} 秒（{worker/60:.2f} 分钟）**，上限21,600秒；该时长包含worker中的CPU初始化与参考计算，不是GPU busy time。原worker {load(P/'execution.json')['old_worker_seconds']:.3f}秒另计。按用户本地资源说明，租赁0元，电费未计。没有联网、安装、SSH、驱动/时钟/功耗设置修改。

运行和失败列表、实际预算、未执行理由、源文件与每个process路径在 `T10_SUPPLEMENT.json`。`derived/t10_supplement/*_sessions.csv`把结果追溯到run/phase；原完整每帧数据保留在对应runs目录。

## 2. S1：加入E_FULL与首尾Native后

每输入固定原sequence0，6块恰好覆盖E/R/M六种中间顺序。每进程先做30秒有用Native路径conditioning；每phase独立至少128次且1秒预热。参考N定义为头尾均值的几何平均；这个定义不保证消除非线性漂移。W2生产N仍为cuSPARSE，E采用与R/M相同rows_per_task和同kernel。W1 E采用同mapped tile body/CTA/occupancy倍数，在普通primary stream执行。

| 输入/程序 | M/N | M/R | E/N | R/E | M/E |
|---|---:|---:|---:|---:|---:|
'''
for inp in ['bonsai','train','ca-GrQc','web-Google','W1','W2']:s+='| '+inp+' | '+' | '.join(ratio(s1[inp+'_'+c]) for c in ['M/N','M/R','E/N','R/E','M/E'])+' |\n'
s+=f'''
数值上，W1的M/N=1.1033，而E/N=1.0903，说明原生到mapped执行组织已解释大部分整体差距；M相对R没有独立增量。W2必须分输入看：ca-GrQc的E/N=0.7392，原生全设备自写同体核可以更快，但分区后M/N=1.4366；web-Google的E/N=1.9152与M/N=1.9262接近，主要差距已出现在自写内核对cuSPARSE的比较中，不能都归咎于分配。

E/N反映原生到table-loop组织的差距；R/E、M/E还包含分区和静态所有权成本。它们是控制比较，不把E提升成最强生产基线，也不能把全部差距归因于某条内存指令。

首尾偏差超过事前5%描述线的块：**{sum(b['drift_flag'] for b in b1)}/24**；全部保留，没有剔除、补跑、时钟回归校正。程序聚合的M/N头锚、尾锚敏感性：

| 程序 | M/N_head | M/N_tail | N_tail/N_head |
|---|---:|---:|---:|
'''
for w in ['W1','W2']:s+='| '+w+' | '+' | '.join(ratio(s1[w+'_'+c]) for c in ['M/N_head','M/N_tail','N_tail/N_head'])+' |\n'
s+='\n![S1与S3比较](supplement/figures/S1_S3_comparisons.png)\n\n![首尾漂移](supplement/figures/S1_anchor_drift.png)\n'
s+=f'''
设备低频轨迹范围（含等待/CPU工作时刻）为 {json.dumps(ranges,ensure_ascii=False)}。监控中的性能限制reason按原样保存，不能由温度快照反推每个phase的限频原因。每块四个进程时间点分开记录；flock串行执行，不把排队重叠当GPU并发。每phase有墙时边界、每帧有完整CPU-ready耗时；没有为旧数据补造不存在的轨迹。

原W1/W2总表还包含sequence1；本轮只重复sequence0，跨轮变化不是同一时间环境下的新随机对照。原K2、组去重、类校准组成、率表、M/R重合率和旧逐块设备快照见 `T10_EVIDENCE_ADDENDUM.md`。

## 3. S2：真正依赖链和同一数据跨位置

固定实际消费0.5/4/32MiB，普通load与.cg，依赖链和有限吞吐分开。每region由虚拟窗口条带组成；依赖链是runtime初始化的全region随机单环，下一次地址取自刚读出的值。每段1024次读取，段间状态延续，整epoch访问全部region。8个重复CTA扩大位置采样但不增加唯一消费集合。所有输入word、虚拟32B sector和128B line计数有数学覆盖证明与footprints记录；每个组消费同一完整集合。分配32MiB与小档只消费0.5MiB分列。

确认采用开发阶段冻结的 **{choice['window_bytes']//1024}KiB 虚拟窗口**；选择规则只用开发覆盖与分轮相关，确认结果未参与选择。但初始实现遗漏CTA任务顺序轮换，开发高相关可能混入固定调度位置；修正生效前allocation3已完成，全部保留为受限证据，allocation4/5采用预先固定的逐轮permutation。没有为凑齐3个修正后确认而突破72配置上限。这是S2的一次有依据修正，故不能把初始相关宣称为已复现物理亲和。经过任务顺序轮换的确认24个size/recipe/access/分配单元（2个独立分配）最小设备SM覆盖 **{smmin}/56**，单region最少覆盖 **{regionmin}个实际SM**。组×region缺格总数 **{sum(p['missing_group_region_round_cells'] for p in probe)}**，SM×region缺格总数 **{sum(p['missing_SM_region_cells'] for p in probe)}**（保留缺格，不填零）。

| 消费集合 | 类型 | 确认早/晚轮Spearman：中位数 [最小,最大] | group×region交互log RMS中位数 |
|---|---|---:|---:|
'''
for size in [524288,4194304,33554432]:
 for access in [0,1]:
  ss=[p for p in probe if p['bytes']==size and p['access']==access];rhos=[p['split_round_spearman'] for p in ss];s+=f"| {size/1048576:g} MiB | {'依赖链' if access==0 else '吞吐'} | {statistics.median(rhos):.3f} [{min(rhos):.3f}, {max(rhos):.3f}] | {statistics.median(p['group_interaction_log_rms'] for p in ss):.5f} |\n"
s+='''
固定CTA顺序的首个“确认”分配，各条件相关的中位数约0.979；加入逐轮任务置乱后的两个确认分配中位数分别约−0.081、−0.102。这不构成“只由顺序引起”的严格同分配消融，但足以否定把初始高相关直接作为稳定地址亲和证据的做法。原始数据和实现修正均保留，不丢弃不利结果。

这里的相关在每个新分配内比较前后轮，不跨分配把相同region号当作相同物理地址。log交互去除了组/SM整体快慢与区域整体快慢；原始ticks与主效应仍保留。依赖链是同一线程的局部clock差；吞吐ticks/word只是CTA完成时间按工作量归一化，**不是单load latency**。微实验分段、准备遍历和局部时钟都不能换算成渲染帧收益。本轮测的是SM/组到数据的访问，不是SM间通信或DSM延迟。

普通/.cg没有证明L1/L2/DRAM实际命中；32MiB大于L2也不是物理域识别。没有收集硬件cache命中/DRAM事务计数。热图只画首个具有顺序控制的确认分配、大档普通依赖链，不能用图的观感替代稳定性或部署对照。

![确认SM残差](supplement/figures/S2_confirm_SM_residual.png)

![确认稳定性](supplement/figures/S2_stability.png)

## 4. S3：实际匹配表、盲表与两置乱

所有条件均做一次完整闭环，不以S2局部效应太小为由省略。2/32MiB×合并/固定索引不规则访问，各6新进程。task固定4KiB、128线程、8次task内完整读取；不规则索引是task内双射，uint64完整CPU结果严格一致。固定50/50配额，同一kernel/launch/join。每个分配重新交叉标定同task在两组的耗时；A按去组主效应的区域相对cost排序，I为盲平衡表，P0交换A两组，P1预定平衡置换。组内始终升序，无每epoch重规划。新A与旧容量M不是同一候选。

每phase32warmup+128测量。位置资格独立于正式测量，逐task记录实际SM与exactly-once；正式kernel关闭位置计数。原始两置乱分别保留，没有挑最慢置乱作参考。

| 条件 | A/N | A/I | A/P0 | A/P1 |
|---|---:|---:|---:|---:|
'''
for inp in sorted(gate['conditions']):s+='| '+inp+' | '+' | '.join(ratio(s3[inp+'_A/'+c]) for c in ['N','I','P0','P1'])+' |\n'
s+='''
2MiB/coalesced 是局部正例：A/I≈0.9422、A/P0≈0.9560、A/P1≈0.9408，在本条件四比较的98.75%区间下均低于1；但A/N≈1.1316，仍慢13.2%，无法部署获益。该结果支持“某些表与该执行组织更匹配”，未排除普通cache/顺序效应。四种条件之间没有再做全族显著性保证，不把这个局部正例包装成普遍硬件规律。

S3也存在测量背景限制：32MiB/coalesced 的N_tail/N_head≈1.2088 [1.1984,1.2186]，尾锚比头锚慢约20.9%。该条件的A/N_head≈1.2278，而A/N_tail≈1.0157，必须结合首尾敏感性阅读；保留全部6块，未据此校正或补跑。它对I/P0/P1也没有稳定优势，故不能只用launch开销解释。

表为95%描述区间；S4进入判断使用每条件四比较Bonferroni调整后的98.75%边际区间、至少3%对N净时间收益和leave-one-block-out同方向。门槛只是本轮投入规则，不是论文成立标准。完整各块比值、调整区间和门槛判定在 `S3_statistics.json`、`S4_gate.json`。所有条件均未通过，不能只以CPU launch解释候选未胜同机制控制的结果。

初始化成本：

| 条件 | 总初始化ms中位数 | 其中标定ms中位数 | 建表ms中位数 | 单表bytes |
|---|---:|---:|---:|---:|
'''
for inp in sorted(gate['conditions']):
 ss=[x for x in initial if x['input']==inp];s+=f"| {inp} | {statistics.median(x['initialization_ms'] for x in ss):.3f} | {statistics.median(x['calibration_ms'] for x in ss):.3f} | {statistics.median(x['plan_construct_ms'] for x in ss):.3f} | {ss[0]['plan_bytes']} |\n"
s+='''
这些成本不算零。phase表另存每次上传时间；总初始化还含CPU期望、资源创建及独立资格，不冒称全部都是候选独有开销。稳态表没有收费初始化摊销；缺少对N的稳定收益时，不能用延长生命周期自动制造回本。A若只在个别同机制对比中占优，也不足以证明当前控制粒度下的部署增量。

## 5. 渲染适配与论文判断

本轮没有触发S4，故没有新增真实tile属性地址枚举、单home混合度、快照重放、scene级A_addr或动态验证。这些格子是NOT_RUN，不填零，也不把S3结果直接套到3DGS。原列表长度分类仍不等于地址亲和。此前“渲染负载可能不适合”的质疑被收窄为可测试命题，尚不能据现有证据断言渲染一定适合或一定不适合。

当前已具备：公开资源组的实际位置证据；同body/同粒度执行组织控制；平衡顺序及首尾锚；同一数据的交叉地址测量；开发/确认分离；实际表部署和同机制盲表/两置乱；完整成本、初始化与正确性证据。仍缺：已确认物理域/裁剪因果机制、可靠且可持续的匹配增量、超越同信息简单基线的新方法、真实动态pipeline净收益、外部强基线及独立器件泛化。本轮没有重新做文献查新，不能主张新颖性已确立。

这批结果可以支撑有界的测量方法、执行成本和负结果分析；**当前不能承诺一项新GPU NUMA优化论文已经成立**。若局部现象只能由缓存/顺序/执行组织解释，应按该层级命名。T10单卡不能反推全部floorsweeping或5070Ti行为。交接仅提供可复用源码和协议，见 `T10_5070TI_HANDOFF.md`。

## 6. 可追溯性与限制

旧索引523行前缀逐字节不变，全部旧M/R哈希不变。新run均有独立目录、编译产物/源码记录和stdout/stderr；原失败不抹除。原程序数值体复用，新增地址kernel的小用例经本地memcheck/synccheck；5次sanitizer均为0 errors，全部正式微诊断单段最大0.655488ms，未超过2ms目标；实际进程执行时间窗无重叠，详细结果见 environment/supplement_final_checks.json 及原日志。未使用新验证框架、特权SM掩码、clock锁定或抢任务runtime。

S2的区域是虚拟地址规则；CUDA分配返回的新进程地址并不保证新物理页。校准local ticks可能受并发、cache、任务顺序及状态影响；正式关闭诊断后计时机制不同，S3正是检验其可部署外推。普通负结果按既定规模收尾，没有补跑寻找赢家。CPU-ready计时包含提交和等待；Green组事件分别展示，max(group_event)从未作为整段makespan。

复现与原始二进制记录格式见 `supplement/REPRODUCE_SUPPLEMENT.md`。全部结果需与范围和缺项一起引用。
'''
(R/'T10_SUPPLEMENT_AND_PAPER_POSITION.md').write_text(s)
print(json.dumps({'capacity_state':capacity,'address_state':affinity,'worker_seconds':worker,'S4':'NOT_TRIGGERED'},ensure_ascii=False,indent=2))
