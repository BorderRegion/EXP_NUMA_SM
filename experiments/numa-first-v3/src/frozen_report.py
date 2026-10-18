"""Chinese report and five scoped evidence fields, with every frozen condition."""
import json,math,csv
import numpy as np
from frozen_common import *
r=runroot();d=json.loads((r/'derived/ANALYSIS.json').read_text());led=[json.loads(x) for x in (r/'ledger.jsonl').read_text().splitlines()];manifest=json.loads((r/'manifest.json').read_text());runtime=sum(x['worker_s'] for x in led);complete=d['status']=='COMPLETE'
def fmt(x,scale=1,center=0):
 if not x:return 'NA'
 return f"{(x['estimate']-center)*scale:+.4f} [{(x['ci'][0]-center)*scale:+.4f}, {(x['ci'][1]-center)*scale:+.4f}]"
def tab(h,rows):return ['| '+' | '.join(h)+' |','|'+'|'.join(['---']*len(h))+'|',*['| '+' | '.join(map(str,row))+' |' for row in rows],'']
def sign(z):
 if not z:return 'NA'
 if z['ci'][0]>0:return '固定正向'
 if z['ci'][1]<0:return '反向'
 return '区间跨0，未分辨'
def ratio(z):
 if not z:return 'NA'
 if z['ci'][1]<1:return '分子更快'
 if z['ci'][0]>1:return '分子更慢'
 return '区间跨1，未分辨'
def delta_direction(z):
 if not z:return 'NA'
 if z['ci'][0]>0:return '交互增加'
 if z['ci'][1]<0:return '交互减少'
 return '差分未分辨'
cs=[x for x in d['mechanism_summary'] if x['subset']=='ALL_COMPLETED'];ds=[x for x in d['deployment_summary'] if x['subset']=='ALL_COMPLETED'];primarym=next((x for x in cs if x['stage']=='S2' and x['size_mib']==2 and x['scope']=='BALANCED56SM' and x['profile']=='H1'),None)
pds=[x for x in ds if x['size_mib']==2 and x['inner_repeats']==1 and x['diagnostic']==0 and x['metric']=='cpu_ready_ms' and (x['method'],x['baseline']) in [('T','N'),('P','M')]]
claims=dict(generated_at=utc(),frozen_rule_repeatability=dict(scope='S1 fixed0x33 and old exact SMsets; no new fit',conditions=[dict(size_mib=x['size_mib'],scope=x['scope'],direction=sign(x['fixed_signed_contrast']),estimate=x['fixed_signed_contrast'],correlation=x['early_late_centered_address_correlation']) for x in d['s1_summary']],unknown='Virtual-region rule is not a physical address hash; allocation processes may recycle physical pages.'),cache_and_order_dependence=dict(scope='S3 minus same-block S2 COMMON and OWNER0-OWNER1',differences=[dict(x,direction=delta_direction(x['difference'])) for x in d['counterfactual_differences'] if x['subset']=='ALL_COMPLETED'],unknown='Primer source/ordering association is not a specific cache-level attribution; no actual cache/DRAM transaction counters.'),low_to_high_concurrency_transfer=dict(scope='S2 L8/L1/H1, CELL and actual JOINT',differences=[dict(x,direction=delta_direction(x['difference'])) for x in d['concurrency_differences'] if x['subset']=='ALL_COMPLETED'],unknown='L8 has8x visits/work; interactions compared, not absolute per-SM communication latency. Actual branch overlap lacks an independent activity timeline.'),diagnostic_free_deployment_effect=dict(scope='S4 FULL, frozen sizes and repeat factors, DIAG0',primary=[dict(comparison=x['method']+'/'+x['baseline'],direction=ratio(x['family_interval']),interval=x['family_interval']) for x in pds],unknown='Same uniform reduction address sets forT/M; no novel layout gain or real application result inferred. Event measurement nodes remain outside clean kernels.'),numa_evidence_level=dict(physical='NOT_ESTABLISHED',empirical='CONDITIONAL: fixed local2MiB and clean low-concurrency effects repeat; full-resource high-concurrency matching remains unresolved, complete-request net gain not established. Report all condition-specific outcomes.',physical_home_known_fraction=0,unknown='No physical-address ownership, memory-domain control, directSM-to-SM latency, or remote traffic proof.0x33 is a virtual region formula.'))
write(r/'derived/CLAIMS.json',claims)
L=['# T10 冻结规则机制实验报告','',f"状态：**{'已完成；条件与限制逐项列明' if complete else '阶段分析，尚有未完成块'}**。生成：{utc()}。",'',f'运行目录：`{r}`。输入包 SHA-256：`7af29547f07704eebb975763fefc428c88e603b786fba80308c4bab612f85da5`。','',
'## 一页结论','',
'本轮把旧开发记录导出的 0x33、方向与确切 SM 集合固定下来。没有重新搜索 mask、翻转 bias 或更换更快资源组。S1 的局部诊断、S2/S3 的无内核诊断四格与实际并发、S4 的 N/T/M/P 含诊断/无诊断分别分析。物理 NUMA 未获确证。','',
f"本轮已结算 {runtime/3600:.4f}/6 GPU-worker 小时；与旧 V3 的 {manifest['parent_used_s']/3600:.4f} 小时合计 {(runtime+manifest['parent_used_s'])/3600:.4f}/24 小时。预算是最大占用，不要求花满。worker 时间含 conditioning、CPU准备、数值和位置资格，不是 GPU busy time。",'',
f"正式完成 {d['phase_count']}/924 phase，{d['epochs']:,} 次 epoch；保存的完整输出检查 {d['saved_full_output_checks']:,} 份，S1 逐 CTA 原值检查 {d['s1_raw_records_checked']:,} 条。6个process/allocation是独立统计单位；不是128epoch或数百万load。缺项 {len(d['missing_plan_ids'])} 个，精确列表见 ANALYSIS.json。",'']
if primarym:L += [f"主要机制条件 FULL/2MiB/H1/COMMON：I_cell×100={fmt(primarym['I_cell_family'],100)}，I_joint×100={fmt(primarym['I_joint_family'],100)}；均为98.75%边际区间。正数支持预先命名的匹配。",'']
for x in pds:L += [f"主要部署条件 FULL/2MiB/HOT one-pass：{x['method']}0/{x['baseline']}0 的完整 output-ready 时间变化 % = {fmt(x['family_interval'],100,1)}；{ratio(x['family_interval'])}（98.75%）。",'']
if complete:
 def mech(size,scope,profile):return next(x for x in cs if x['stage']=='S2' and x['size_mib']==size and x['scope']==scope and x['profile']==profile)
 def dep(method,baseline,metric,diag=0):return next(x for x in ds if x['size_mib']==2 and x['inner_repeats']==1 and x['method']==method and x['baseline']==baseline and x['diagnostic']==diag and x['metric']==metric)
 low1=mech(2,'BALANCED56SM','L1');low8=mech(2,'BALANCED56SM','L8');high=mech(2,'BALANCED56SM','H1');pair=mech(2,'PAIR4SM','H1')
 bridge=next(x for x in d['concurrency_differences'] if x['subset']=='ALL_COMPLETED' and x['size_mib']==2 and x['scope']=='BALANCED56SM' and x['comparison']=='H1-L1' and x['metric']=='I_joint')
 owner=next(x for x in d['counterfactual_differences'] if x['subset']=='ALL_COMPLETED' and x['scope']=='PAIR4SM' and x['profile']=='OWNER0_MINUS_OWNER1' and x['metric']=='I_joint')
 delta=next(x for x in ds if x['size_mib']==2 and x['inner_repeats']==1 and x['method']=='delta_diag' and x['metric']=='batch_per_request_ms')
 L += ['**对十个问题的直接解释：**','',
 '1. **旧规则确实能迁移到新进程的局部诊断。** 两个2MiB scope都保持旧方向，早晚相关约0.997–0.998；这次没有重新选择方向，因而不能把重复现象全归因于每次重新拟合。',
 f"2. **低并发优势不是必须靠8次visit或内核诊断才能出现。** clean FULL的L8 joint log优势×100={fmt(low8['I_joint'],100)}，L1={fmt(low1['I_joint'],100)}（95%）。L1也只消费一遍；但每组只有2CTA，不能把此结果叫全56SM吞吐收益。",
 f"3. **高并发FULL尚未分辨匹配优势。** H1 joint×100={fmt(high['I_joint'],100)}（95%）；H1-L1的配对交互差×100={fmt(bridge['difference'],100)}。后者仍跨0，所以只说明没有可靠迁移证据，不能证明优势一定归零，或精确断言并发造成多少损失。",
 f"4. **CELL不能代替JOINT。** 2MiB PAIR/H1 的CELL交互×100={fmt(pair['I_cell'],100)}，为反向；其JOINT×100={fmt(pair['I_joint'],100)}，未分辨。32MiB也出现CELL与JOINT符号不同的条件，完整表保留，未把隔离格加总当并发结果。",
 f"5. **至少一个owner相关差分可分辨，不能推广到所有scope。** PAIR的OWNER0-OWNER1 joint交互差×100={fmt(owner['difference'],100)}（95%探索性）；支持该条件与先前读取者关联。FULL的owner、payload和128B平移差分区间仍较宽，未排除0；不能据此证明内容无关、平移不变或已定位某一级cache。标签重命名仅为CPU代数控制。",
 f"6. **诊断能改变部分批量对比，但不是已确证的唯一解释。** 新共同消费者中，2MiB repeat1的batch delta_diag×100={fmt(delta['effect'],100)}（95%探索性）；完整请求的诊断差分则仍未分辨。不能用batch的观察效应替代整个请求的机制结论，也未与旧批次绝对时间相减。",
 f"7. **clean部署净收益尚未建立。** 2MiB repeat1，M0/T0完整请求变化%={fmt(dep('M','T','cpu_ready_ms')['effect'],100,1)}（95%探索性）；M0/N0={fmt(dep('M','N','cpu_ready_ms')['effect'],100,1)}。均不支持本实现的联合布局增量；T0/N0及反向主比较的98.75%区间见上。其他大小/复用/指标正负都保留。",
 '8. **运行状态有记录，物理解释仍有限。** 六块没有已定义的cap/thermal状态改变；动态频率、功耗尖峰、桌面服务和短phase状态分辨率限制均保留。没有把稳定上限说成锁频或恒定实际功耗。',
 '9. **本轮支持条件性的经验关系；物理NUMA仍未建立。** 确切SM资源和固定地址类可以真实干预，局部及低并发出现重复方向；没有物理home、PA、服务域或远端流量证据，也没有独立活动时间线确认两个分支重叠。',
 '10. **现阶段不直接扩大真实应用。** 已有局部/低并发机会，但全资源clean完整请求净收益和高并发匹配仍未成立。后续若另立小实验，应先提高高并发对比的辨识度并核实实际并行推进；本轮不追加块数、换mask或部署应用来追正值。','']
L += ['局部规律能重复、并发完成有益、相对原生有净增量，是不同命题。下表完整展示正负方向；不能只取最好的一项或把区间跨零称为完全等效。','',
'## 1. 冻结对象与执行合同','',
'旧 fine_shift_0 开发2MiB CSV与原字节 SHA 已核对；PAIR4SM C0={24,25}、C1={20,21}、bias1；FULL两个确切28SM集合、bias0均从旧完整资源对象的实际 roster 重建。本轮每进程重新观察并匹配实际集合，未假定旧group编号永久有效。两种大小都使用0x33，不为32MiB拟合自己的规则。详见 RULE_SOURCE_CHECK.json、FROZEN_RULE.json、各membership.csv。','',
'每块一个32MiB+4096B自有分配；2MiB为前缀，OFFSET128在相同大分配内平移128B，scratch为独立128MiB。VA、容量、generation保留，物理页独立性未知。同块保留allocation与context，按S1→S2→S3→S4完成，然后才启动下一进程；避免跨阶段换分配。','',
'正式S2/S3各epoch预建Graph固定primer→consumer顺序，无逐任务host规划或GPU调度表；四个仿射任务置换(a,b)=(1,0),(5,3),(13,7),(29,23)按epoch循环，六动作完全一致。S4自然次序a1/b0。完整原phase计划与执行顺序逐ID保留，未按性能改序。S4只用Williams8的预定六行，不声称完整八行平衡。','',
'## 2. S1：固定方向的局部复验','',
'原移位probe不改二进制；28个2SM资源、4轮、grid2、512 region-task、.cg one-pass、同组warmup。该路径保留SM/clock诊断，与clean消费不混池。以下按每块四轮汇总，再重采样六块。相关性表示形状稳定，不是提速或home分类正确率。','']
L+=tab(['MiB','scope','固定方向log对比×100 [95%]','早晚轮地址相关 [95%]','方向'],[[x['size_mib'],x['scope'],fmt(x['fixed_signed_contrast'],100),fmt(x['early_late_centered_address_correlation']),sign(x['fixed_signed_contrast'])] for x in d['s1_summary']])
L+=['每轮和每块的region对比在s1_rounds/s1_region_contrasts；原CTA ticks、SM、region、sum及缺格保留。代表raw/residual/coverage图固定取block0，其他块均在完整数据与逐块曲线中，未挑最好热图。','',
'## 3. S2：四格原始值与低→高并发','',
'固定D(r)=parity(r&0x33) XOR scope_bias；out[64*visit+r]固定，不随计算归属变动。CELL只读一类、半个集合；JOINT同时提交两组后统一join，读全体。L8每类32region×8完整visit，L1/H1一次visit；grid分别2/2/32 CTA每组。PAIR只有4SM，H1的32CTA不等于32SM。','',
'`I_cell=0.5*(logT01+logT10-logT00-logT11)`；`I_joint=log(T_reverse/T_match)`。以下均为consumer span，准备在外单列。L8与L1有8倍工作/复用差异，不能直接相减称NUMA延迟。logical_load_bytes不当作DRAM流量。','']
s2=[x for x in cs if x['stage']=='S2'];L+=tab(['MiB','scope','profile','I_cell×100 [95%]','I_joint×100 [95%]'],[[x['size_mib'],x['scope'],x['profile'],fmt(x['I_cell'],100),fmt(x['I_joint'],100)] for x in s2])
L+=tab(['MiB / scope / profile','T00 us [95%]','T01 us [95%]','T10 us [95%]','T11 us [95%]','MATCH us [95%]','REVERSE us [95%]'],[[f"{x['size_mib']} / {x['scope']} / {x['profile']}",*[fmt(x['cell_times'][k],1000) for k in ['C0_D0','C0_D1','C1_D0','C1_D1','J_MATCH','J_REVERSE']]] for x in s2])
L+=['CELL是在另一组没有人为dummy任务的隔离场景；它对JOINT的预测不自动成立。每块原始格和有符号交互全部保留；独立的重叠活动时间线缺失，所以Graph结构、有效fork/join与输出ready makespan不冒称已经直接测量两组同时活跃。','',
'## 4. S3：owner、内容、标签与基址','',
'OWNER_C0/1都读取整个集合，仅执行资源改变；COMMON由primary全资源固定sweep；SCRATCH真正扫描128MiB自有数据，但不保证硬件flush。每个测量epoch都执行相同准备配方，非只在phase开始一次。payload互换仅改value(r XOR1,k)，load地址和类不改。OFFSET128实际改变地址，mask方向仍固定。','']
L+=tab(['profile','scope','I_cell×100 [95%]','I_joint×100 [95%]'],[[x['case_id'],x['scope'],fmt(x['I_cell'],100),fmt(x['I_joint'],100)] for x in cs if x['stage']=='S3'])
L+=['以下是同块配对差分，避免用两段区间是否重叠代替干预差分。正负均保留。','']
L+=tab(['profile / scope','对比','指标','交互差×100 [95%]'],[[x['profile']+' / '+x['scope'],x['contrast'],x['metric'],fmt(x['difference'],100)] for x in d['counterfactual_differences'] if x['subset']=='ALL_COMPLETED'])
L+=['RELABEL令alias=r XOR1，只在CPU重新标注S2 COMMON原样本，补偿parity(alias&0x33) XOR1 XORbias后等于旧D(r)。64个region逐一验证，交互原值保持；没有新增GPU phase或第二份独立证据。base-shift失效只能限制虚拟坐标规则的适用域；owner关联也不能在缺counter时定位某一级cache。','',
'## 5. S4：去除内核诊断后的真实基线','',
'clean/diag由编译期模板分别生成cubin。clean的class1/class8/native1 SASS没有SM/clock读取、atomic或诊断record写入；每个入口只保留一次静态数值sum store位置。不是传diag=nullptr。DIAG1/0寄存器、shared与代码差异原样保留，未填dummy指令。详见compiled/build.json、diag0/1 SASS和ptxas日志。','',
'每个clean phase使用相同context/scalar绑定的DIAG1 sibling在前后独立资格；保存clean实际数值输出，位置记录只属于sibling，未声称观测了每次clean物理位置。S2/S3两个实质计算分支或一个CELL，加一个准备kernel；S4 N一个数学kernel，T/M/P两个，没有planner kernel。计时Graph另外有3个event-record节点和child结构；它们是共同观测成本，不是内核诊断消失后整个程序完全无观测。','',
'N全56SM、64CTA；T固定亲和分配原布局，M同资源算术着色，P只反转M归属。T/M物理读取集合相同，输出/内容关联和布局成本有别。各128次output-ready；HOT无人工primer。每policy至少32epoch且100ms同配方warmup。batch次数只在开发N上按20–100ms目标冻结128..8192，各policy相同、未改变inner_repeat。batch图只有消费者，使用外层事件，避免请求图里的event节点覆盖batch计时。','']
for metric,title in [('consumer_ms','Consumer GPU span'),('cpu_ready_ms','完整 output-ready'),('batch_per_request_ms','紧密batch每请求')]:
 L+=['### '+title,''];L+=tab(['MiB','repeat','比较','DIAG','时间变化 % [95%]','绝对差 us [95%]'],[[x['size_mib'],x['inner_repeats'],x['method']+'/'+x['baseline'],x['diagnostic'],fmt(x['effect'],100,1),fmt(x['absolute_difference'],1000)] for x in ds if x['metric']==metric and x['method']!='delta_diag'])
L+=['`delta_diag=log(P1/M1)-log(P0/M0)`；以下是整体观察版本对匹配对比的影响，不是某一条clock/store指令的独立成本。','']
L+=tab(['MiB','repeat','metric','delta_diag×100 [95%]'],[[x['size_mib'],x['inner_repeats'],x['metric'],fmt(x['effect'],100)] for x in ds if x['method']=='delta_diag'])
L+=['## 6. 状态、成本、预算与未测项','',
'各进程先用实际clean T消费者在FULL冻结资源组交替消费2/32MiB，最多180秒conditioning。100W是请求/执行上限，不是恒定实际功率或锁频。保留动态频率、温度、NVML限制原因、风扇记录与原保护服务；没有管理员入口时只记录一次POWER_CONTROL_LIMIT，不循环写功耗或取消降额。','',
f"已完成块状态：{[(x['block'],x['status'],x['reasons']) for x in d['state']]}。ALL_COMPLETED和STABLE_STATE结果都在ANALYSIS.json；稳定子集仅按cap/thermal状态选择，不按性能或频率。主表展示所有完成块，保留温度/功耗尖峰和N首尾漂移。1Hz字段依次查询，短phase可能没有状态样本；未插值、未做时钟回归。phase窗口含请求间隔/末检查/batch，不能伪称逐kernel实际频率。",'',
'输入生成/上传、Graph build、资源/context重建、完整数值与位置检查属于一次性或研究过程，分别留在phase/worker记录。每请求准备/consumer/完整GPUspan/CPU-ready分别保存；S4 HOT无逐请求布局更新。未将本轮固定规则的研究成本全部算作部署成本，也没有假定必要上下文和布局免费。若稳态未更快，不宣称无限摊销可回本。','',
'已有toolkit-bin sanitizer最初缺注入库，在目标启动前失败；记录保留。改用本机已存在的完整12.8.93 bundle后，有限memcheck成功，无GPU代码变更或下载安装。未发现可调用的现成Nsight时间线/counter工具；0/4 profile captures，列NA。CUPTI API调用计数工具不当作重叠或流量证据。','',
'本轮没有第二功耗档、第三种大小、新mask、渲染/CSR/LLM候选，也没有直接SM-to-SM通信、物理home、PA或远端事务证据。这些未测不解释为不存在。受支持Green资源是计算集合，不提供本机物理内存域身份。','',
'## 7. 五项证据字段与下一步边界','',
'机器可读结论在derived/CLAIMS.json，保留每个scope/大小/并发/primer/诊断版本的方向与unknown。可能同时存在局部高度重复、并发消失/反转、条件性正收益与物理home未知，不压成单个GO/STOP。','',
'只有在clean真实消费的正确匹配优于反向，并能超过简单T或完整N的相应基线时，才有依据讨论下一项应用验证。本轮即使局部正向，也不自动证明真实应用收益或新算法；若M≈T，则仅支持静态亲和工程机会。没有3%/5%作为省略实验门槛。','',
'## 8. 复算与原始索引','',
'主资料：FROZEN_RULE.json、PHASE_PLAN.jsonl、EXECUTION_FREEZE.json、ANALYSIS_CONTRACT.json、compiled源码/cubin/SASS；raw/block_*/包含逐epoch时间、S1 CTA原值、完整输出/位置sibling、原子done记录和遥测。derived/ANALYSIS.json同时包含每块和汇总、四格原值、状态子集、配对差分和label控制。','',
'图在figures/，全部从raw分析生成：s1_fixed_region_contrast / s1_raw_and_residual / s1_sm_missing_cells / four_cell_raw_times / concurrency_bridge / cache_and_coordinate_controls / diagnostic_free_absolute_times / clean_deployment_ratios / diagnostic_interaction_difference / consumer_and_preparation_costs / telemetry_and_native_anchors。每图有PNG与PDF。','',
'最终RESTORATION_REPORT.json只读核对原控制文件SHA、服务、100W和实验进程退出；本轮没有修改硬件控制，正常结束无需写回。小包提供全部本轮raw、代码和独立CPU复算脚本，不复制旧模型/toolkit/巨型历史raw。旧V3数据只读引用，其已用预算与新账分别保留。','']
runtime_path=r/'derived/RUNTIME_SUMMARY.json'
if runtime_path.exists():
 runtime_data=json.loads(runtime_path.read_text());a=runtime_data['all_worker_samples'];phase=runtime_data['measured_phase_window_samples']
 details=['### 实测运行范围','']+tab(['全部worker的1Hz样本','min','median','p95','max'],[[label,*[f"{a[key][q]/scale:.3f}" for q in ['min','median','p95','max']]] for key,label,scale in [('temperature_c','温度C',1),('power_mw','采样功耗W',1000),('sm_mhz','SM MHz',1),('mem_mhz','显存MHz',1)]])
 details += [f"请求/执行cap样本：{runtime_data['requested_cap_mw']} / {runtime_data['enforced_cap_mw']} mW；高于同次执行cap的采样功耗 {runtime_data['power_above_concurrent_cap_samples']} 个，保留且未独立诊断尖峰来源。全部样本 {a['temperature_c']['n']} 个，落入实际测量phase窗口 {phase['temperature_c']['n'] if phase['temperature_c'] else 0} 个；后者也含host间隔/末检查/batch，并非逐kernel频率。",'',f"S4实际batch事件跨度范围 {runtime_data['batch_span_ms']['min']:.3f}–{runtime_data['batch_span_ms']['max']:.3f} ms；{runtime_data['batch_span_ms']['outside20to100']}/{runtime_data['batch_span_ms']['phases']} 个phase超出20–100ms开发目标，均原样保留，未为候选改重放次数。",'']
 at=L.index('## 7. 五项证据字段与下一步边界');L[at:at]=details
(ROOT/'T10_NUMA_FROZEN_RULE_MECHANISM_REPORT.md').write_text('\n'.join(L).rstrip()+'\n')
P=['# 物理 NUMA 与经验结果的边界','',
'已直接观察：固定旧规则在新进程内的原始CTA cycles、四格与真实joint完成span、DIAG0/1数值/时间；前后diagnostic sibling的真实SM位置；完整输出、实际Graph节点和运行状态。','',
'可按条件讨论：固定方向能否重复；owner/内容/base变化是否关联交互；低并发到高并发的交互变化；clean匹配是否优于反向、T或N。所有方向与区间见主报告和CLAIMS.json。','',
'仍然未知：物理内存home和PA、cache slice/DRAM/remote traffic、两计算分支实际重叠活动时间线、每次短kernel实际频率、直接SM-to-SM通信延迟。Green分组、虚拟region和0x33不提供这些身份。','',
'关键限制：只有6个进程/分配块；物理页可能复用；S1有观察与多次region复用；L8有8倍任务；primer不是保证相同cache；S4六行不是完整Williams8平衡；clean Graph仍有测量event；T/M在均匀归约中读取相同地址集合。','',
'物理NUMA结论：NOT_ESTABLISHED。允许条件性经验亲和与缓存/并发关联的正负事实同时成立；不以此证明所有GPU均匀或非均匀。真实应用优化和论文新颖性需要独立证据。','']
(ROOT/'PHYSICAL_VS_EMPIRICAL_CLAIMS.md').write_text('\n'.join(P).rstrip()+'\n')
T=['# 给导师的简短说明','',f"本轮固定旧0x33与确切SM集合，新增{runtime/3600:.3f} GPU-worker小时，完成{d['phase_count']}/924个phase；没有重新选择方向。",'']
for x in d['s1_summary']:
 if x['size_mib']==2:T.append(f"局部2MiB {x['scope']}：固定log对比×100={fmt(x['fixed_signed_contrast'],100)}，早晚相关={fmt(x['early_late_centered_address_correlation'])}。")
if primarym:T+=['',f"clean FULL/H1：I_cell×100={fmt(primarym['I_cell_family'],100)}；joint×100={fmt(primarym['I_joint_family'],100)}（98.75%）。"]
for x in pds:T.append(f"完整请求{x['method']}0/{x['baseline']}0变化%={fmt(x['family_interval'],100,1)}，{ratio(x['family_interval'])}。")
T+=['','owner、payload、label及128B平移的配对结果与DIAG差分全部保留在主报告。是否值得继续应用，须同时看真实并发匹配和强基线；不能用局部热图替代。','', '本轮仍未识别物理home或远端流量，未执行应用部署；结果最多按具体访问和执行条件讨论。保护配置保留，恢复核查与复算记录随包交付。']
if complete:T.insert(4,f"关键进展：clean低并发FULL的L1 joint log优势×100={fmt(low1['I_joint'],100)}，L8={fmt(low8['I_joint'],100)}（95%）。因此现象不必依赖内核诊断或8次visit；高并发区间较宽，尚不能断言效果已归零。")
(ROOT/'T10_FROZEN_RULE_导师稿.md').write_text('\n'.join(T).rstrip()+'\n')
print('report written',d['status'])
