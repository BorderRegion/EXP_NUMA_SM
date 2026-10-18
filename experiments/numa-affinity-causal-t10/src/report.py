from common import *
import numpy as np,collections
SCOPES=['ready','fresh','batch','freshbatch'];NAMES={'ready':'热输入，单次','fresh':'重写输入→Softmax，单次','batch':'热输入，32次连续','freshbatch':'每次重写输入，32次连续'}
def run():
 a=read(ROOT/'derived/AUDIT.json');results=read(ROOT/'derived/confirm.json')['results'];dev=read(ROOT/'derived/dev.json')['results']
 def get(V,var,scope,comp,page=17,metric='gpu'):return next(x for x in results if x['V']==V and x['variant']==var and x['scope']==scope and x['page']==page and x['comparison']=='MINIMAX/'+comp and x['metric']==metric)
 def f(x,ci='ci95_pct'):return f"{x['gain_pct']:+.3f}% [{x[ci][0]:+.3f}, {x[ci][1]:+.3f}]"
 controls=['IDENTITY','RANDOM_BEST','POOLED','WRONG_ADDRESS'];primary=[get(131072,'BOTH',s,c) for s in SCOPES for c in controls];passed=all(x['ci996875_pct'][0]>0 for x in primary)
 basepassed=all(get(131072,'BOTH',s,c)['ci95_pct'][0]>0 for s in SCOPES for c in ['BASE_IDENTITY','BASE_MINIMAX'])
 write(ROOT/'derived/DECISION.json',dict(primary_16_comparisons_all_positive=passed,faster_than_both_prior_baselines_all_scopes=basepassed,default_enable=False,reason='Experimental only; no automatic deployment or physical NUMA inference.',primary=primary))
 def table(V,var,page=17):
  lines=['| 运行条件 | 固定配对 | 开发选出的最强随机 | 忽略地址的 pooled | 错误地址 |','|---|---|---|---|---|']
  for s in SCOPES:lines.append('| '+NAMES[s]+' | '+' | '.join(f(get(V,var,s,c,page)) for c in controls)+' |')
  return '\n'.join(lines)
 def factorial(V):
  lines=['| 条件 | 内核变体 | 相对固定配对 | 相对最强随机 |','|---|---|---|---|']
  for s in SCOPES:
   for var in ['OLD','BAL','FIX','BOTH']:lines.append(f"| {NAMES[s]} | {var} | {f(get(V,var,s,'IDENTITY'))} | {f(get(V,var,s,'RANDOM_BEST'))} |")
  return '\n'.join(lines)
 absrows=['| 条件 | MINIMAX µs/次 | 原快核固定配对 µs/次 | 相对原快核固定配对 | 相对原快核地址配对 |','|---|---:|---:|---|---|']
 for s in SCOPES:
  x=get(131072,'BOTH',s,'BASE_IDENTITY');b=32 if 'batch' in s else 1;absrows.append(f"| {NAMES[s]} | {x['method_mean_us']/b:.4f} | {x['control_mean_us']/b:.4f} | {f(x)} | {f(get(131072,'BOTH',s,'BASE_MINIMAX'))} |")
 host=['| 条件 | 主机区间相对固定配对 | 主机区间相对最强随机 |','|---|---|---|']
 for s in SCOPES:host.append(f"| {NAMES[s]} | {f(get(131072,'BOTH',s,'IDENTITY',metric='host'))} | {f(get(131072,'BOTH',s,'RANDOM_BEST',metric='host'))} |")
 diag=read(RUN/'diagnose/trace_summary.json');z=collections.defaultdict(list)
 for x in diag:
  if x['V']==131072 and x['scope']=='ready' and x['policy']=='MINIMAX':z[x['variant']].append(x)
 traced=['| 变体 | 每SM有效元素范围 | 观测归并者SM | 本地计算中位数 ns | 消费者交接段中位数 ns | 归并者等待中位数 ns |','|---|---|---|---:|---:|---:|']
 for v,rr in sorted(z.items()):traced.append(f"| {v} | {min(x['work_min'] for x in rr)}–{max(x['work_max'] for x in rr)} | {sorted(set(x['collector'] for x in rr))} | {np.median([x['local_median_ns'] for x in rr]):.1f} | {np.median([x['consumer_handoff_median_ns'] for x in rr]):.1f} | {np.median([x['collector_wait_ns'] for x in rr]):.1f} |")
 setup=collections.defaultdict(list)
 for p in RUN.glob('confirm_*/V131072/BOTH/*/page17/config.json'):
  x=read(p)
  for pol in ['MINIMAX','IDENTITY','BASE_IDENTITY']:setup[x['scope'],pol]+=x['setup_ms'][pol]
 setups=['| 条件 | MINIMAX建图 ms | IDENTITY建图 ms | 原快核固定配对建图 ms |','|---|---:|---:|---:|']
 for s in SCOPES:setups.append('| '+NAMES[s]+' | '+' | '.join(f'{np.median(setup[s,p]):.3f}' for p in ['MINIMAX','IDENTITY','BASE_IDENTITY'])+' |')
 aa=read(ROOT/'derived/BASELINE_AA.json')['results'];aatable=['| 条件 | OLD固定配对/原二进制固定配对 | OLD地址配对/原二进制地址配对 |','|---|---|---|']
 for scope in SCOPES:aatable.append('| '+NAMES[scope]+' | '+' | '.join(f(next(x for x in aa if x['scope']==scope and x['metric']=='gpu' and x['comparison']=='OLD_'+p+'/BASE_'+p)) for p in ['IDENTITY','MINIMAX'])+' |')
 secondary=read(ROOT/'derived/SECONDARY.json')['results']
 supplement=['| 条件 | 变体 | POOLED/固定配对 | POOLED/最强随机 | POOLED/原快核固定配对 |','|---|---|---|---|---|']
 for scope in SCOPES:
  for var in ['OLD','BAL','FIX','BOTH']:
   zz=[next(x for x in secondary if x['V']==131072 and x['variant']==var and x['page']==17 and x['scope']==scope and x['metric']=='gpu' and x['comparison']==c) for c in ['POOLED/IDENTITY','POOLED/RANDOM_BEST','POOLED/BASE_IDENTITY']]
   supplement.append('| '+NAMES[scope]+' | '+var+' | '+' | '.join(f(x) for x in zz)+' |')
 timing=read(ROOT/'derived/TIMING_SENSITIVITY.json');sens=['| 条件 | 主结果全部8次：相对固定配对 | 仅后4次敏感性：相对固定配对 | 仅后4次：相对原快核 |','|---|---|---|---|']
 for scope in SCOPES:
  z=[next(x for x in timing['results'] if x['scope']==scope and x['window']==w and x['comparison']==c) for w,c in [('all8','MINIMAX/IDENTITY'),('last4','MINIMAX/IDENTITY'),('last4','MINIMAX/BASE_IDENTITY')]]
  sens.append('| '+NAMES[scope]+' | '+' | '.join(f(x) for x in z)+' |')
 stability=read(ROOT/'derived/ANCHOR_STABILITY.json')['summary']
 stable='\n'.join(f"- {NAMES[s]}：{v['blocks']} 对首尾锚点中，{v['absolute_change_gt3pct']} 对变化超过3%；不据此删除任何样本。" for s,v in stability.items())
 text=f'''# T10：均衡工作与固定归并者后的地址亲和因果复验

运行 `{RUN.name}`。百分比统一为 `100×(1−T_MINIMAX/T_control)`，正数表示完整耗时减少。下表默认95%进程bootstrap区间；预定义16项主要对照另保存99.6875%区间。

## 结论范围

本轮已完成。预定义主条件是 **131072词表、邮箱页17、均衡工作且固定SM1归并（BOTH）**。16项主要地址对照全部通过保守区间的判定为 **{'通过' if passed else '未通过'}**；四种运行条件下同时快于上一轮两个快核对照的判定为 **{'通过' if basepassed else '未通过'}**。默认不启用实验映射；不能把均衡布局或归并结构本身的收益记为地址亲和收益。

严格主条件的地址配对相对同内核固定配对，热输入点估计为 **{get(131072,'BOTH','ready','IDENTITY')['gain_pct']:+.3f}%**，每次重写输入为 **{get(131072,'BOTH','fresh','IDENTITY')['gain_pct']:+.3f}%**。新完整内核在四种条件下相对原快核固定配对都退化约 **2.8%–4.3%**。后4次调用的事后敏感性分析也没有改变这一结论，原快核继续保留。

上一轮的局部热输入正数不作为本轮结论。这里使用新输入、新进程、独立开发选出的最强随机方案，并同时保留单次、输入重写和连续运行结果。当前没有物理SM屏蔽坐标、通用NUMA域或整模型tokens/s的结论。

## 实现与因果对照

| 变体 | logits工作分布 | 最终归并者 |
|---|---|---|
| OLD | 原128元素条带 | 最后抵达的消费者 |
| BAL | 连续分区，尽量等量 | 最后抵达的消费者 |
| FIX | 原128元素条带 | 固定SM1 |
| BOTH | 连续分区，尽量等量 | 固定SM1 |

131072词表的原布局每SM处理2304或2432个元素；均衡后为2340或2341。额外129024尺寸能完全均分，每SM2304个元素，用作机制控制。均衡同时改变了访存分布/对齐，故BAL相对OLD的变化并非纯粹的负载均衡因果证据；每个变体内部的配对比较保持工作分配不变。

四变体维持56个cooperative CTA、每CTA128线程、48KiB动态共享内存保留，运行时要求occupancy为1，并以trace验证56个SM各出现一次且起止一致。SM1固定归并需等待28个消费者完成，等待成本全部计时。相同变体的策略只改变常量参数中的配对，不增减计算或通信消息，不在热态建表/上传/分配。一个完整配对Softmax仍为一个kernel；fresh多一个真实copy；32次连续条件保留全部32次初始化、同步、复位和launch间隙。

131072未插桩版本的寄存器数为OLD 70、BAL 75、FIX 72、BOTH 79；编译日志均为0字节stack/spill。occupancy仍由48KiB共享内存保留限制为1，额外地址指令和等待仍可能有成本，不归因于某一项单独原因。详见 `derived/RESOURCES.json`。

未插桩OLD的131072版本以及普通两阶段partial/finish，与上轮机器指令逐项相同；原二进制另作为BASE_IDENTITY、BASE_MINIMAX直接对照。由此把编译变化和基线退化的风险显式纳入核验。

## 主要结果：131072，BOTH，预选页17

{table(131072,'BOTH')}

主结果16项的99.6875%区间、六个进程各自符号和完整统计在 `derived/DECISION.json` 与 `reports/RESULTS_COMPACT.json`。RANDOM_BEST是每条件在两个开发进程中从12套随机映射选出的最快者；确认前冻结，测试后不再换赢家。POOLED使用旧三个地址训练矩阵的均值拟合一张共用映射；WRONG_ADDRESS使用其它地址的冻结映射。随机平均也完整保留，但不替代最强随机对照。

![Address controls](figures/controls.png)

## 是否快过上一轮完整快核

{chr(10).join(absrows)}

绝对时间栏是块内中位数的算术平均；百分比来自配对几何比，不直接由两栏均值相除。批量绝对时间为完整batch事件时间除32，含每次收尾与初始化、kernel间隙；它是平均吞吐代价，不能冒充单token响应延迟。即使同一慢内核内部出现配对增量，也只有超过完整旧快核才有工程净收益。普通两阶段NATIVE也保留；普通融合差额不算NUMA。

指令相同的OLD与原二进制还保留了性能层面的一致性诊断（单独函数入口/地址和Graph可能不同；这不是新增调参）：

{chr(10).join(aatable)}

这里不是严格同一二进制的A/A：函数入口、参数元数据、代码位置和Graph不同，差异来源尚未隔离，不能直接称为纯计时噪声。这些差异不能凭“机器指令一样”自动当成零；原二进制作为强基线直接保留。主性能比较没有按此诊断校正或删样。

## 四变体拆分与完全均分控制

131072词表：

{factorial(131072)}

129024完全均分尺寸：

{factorial(129024)}

129024是诊断尺寸，没有声称运行了使用该词表的真实LLM。BOTH在地址页0、257的全部额外控制同样保留于紧凑结果；邮箱页17沿用前轮训练预选，没有依据本轮计时重新选址。

## 补充：忽略地址的SM模型是否更有效

用户目标也包括一般SM拓扑调度，因此额外保留POOLED和开发选出的随机策略本身的比较。这项分析在确认执行中、尚未读取确认耗时估计时补充，属于探索性分析，不更改原16项主要判定或使用确认数据选策略。全部条件的随机赢家结果保存在 `derived/SECONDARY.json`，随机搜索收益不能归为地址或拓扑因果。

{chr(10).join(supplement)}

## 主机、输入与初始化开销

{chr(10).join(host)}

GPU起止事件与计算子图位于同一张CUDA Graph，沿用旧二进制计时包装器；实际执行图的节点数和顺序另外核验。主机计时为C++提交至stream-ready，不含Python调用包装、输入H2D/输出D2H。fresh是实际copy当前输入再执行Softmax，未模拟LM-head矩阵乘法；四份随机logits轮换，每个block内多次请求使用同一份内容。没有运行真实权重、完整生成或top-k/top-p。

每个实验Job的建图中位数（含两次热身，不含Data分配、模型校准和冷启动CUDA）如下，不能当成完整一次性初始化成本：

{chr(10).join(setups)}

旧设备模型直接离线复用，本轮没有在每个新workspace上重新校准。模型以相对邮箱页和SM身份为索引，没有解析物理home；2MiB虚拟对齐不能证明物理home相同。本轮两个词表Data同时驻留，分配顺序也不同于上一轮，因此本轮跨分配迁移失败不能被解释成“任何地址相关性都不存在”。各条件内部所有策略仍共享同一输入/输出和邮箱地址；实际部署若要求重校准，应另计成本。逻辑邮箱2MiB，为对齐分配4MiB。原快核仍保留，实验夹具不是成熟推理框架API。

## 插桩诊断与机制核验

131072、热输入、MINIMAX，每组16次：

{chr(10).join(traced)}

![Verified work and collectors](figures/mechanism.png)

诊断另编译带时间戳/存储的trace版本，正式计时不含它。交接段包含邮箱等待、数据归并、原子fan-in等；它不等于单向物理链路时间。时间戳和trace写入改变调度，thread0阶段也不是整个CTA完成时刻，因此这些数值只用于机制核验和定位，不用于分摊正式收益的纳秒因果贡献。

工作均衡和固定归并者并没有抹平所有因素：相同元素数不保证相同抵达时刻，原子fan-in、最终通知、缓存、时钟和物理页复用依然存在。SMID仅为调度身份，不是芯片坐标，见[NVIDIA PTX SMID说明](https://docs.nvidia.com/cuda/parallel-thread-execution/index.html#special-registers-smid)。消息发布/获取使用GPU范围release/acquire和原子同步，内存排序语义见[NVIDIA PTX内存模型](https://docs.nvidia.com/cuda/parallel-thread-execution/index.html#memory-consistency-model)。本轮没有调用未公开SM屏蔽接口。

## 首次调用与连续调用的事后敏感性分析

首尾锚点并非同样的热态条件：后续块的前锚点发生在上一块CPU处理/落盘之后，后锚点紧随一段GPU请求。第一轮请求比后续请求慢，不能把它全部称为随机漂移，也不能在没有额外控制时只归因于时钟。主条件各scope中，策略内第1次计时相对后4次中位数，中位数约高7.1%、12.7%、8.0%、8.3%。

原定主统计仍使用完整8次的中位数，不删除任何样本。下面只用已有数据做事后敏感性分析，考察后4次的连续热态结果；批量条件下的一次计时指含32个完整请求的整组Graph，后4次也指后4组Graph。它不是冷启动/首次请求延迟，也不替代主结果：

{chr(10).join(sens)}

完整新内核相对旧快核的退化仍存在。未来若继续讨论不到1%的增量，需把首次调用、固定提交间隔和连续稳态分别设计，避免让CPU落盘间隙或不同编译入口混入拓扑解释。

## 统计、稳定性及完整性

先取随机块内计时中位数，再计算同块配对log比，最后按进程等权聚合。30000次bootstrap以整个进程重采样，保留95%和针对16项主要对照的99.6875%区间。六个进程来自同一卡同一天，区间不覆盖整个连续研究历史，也不是跨硬件置信度。所有开发、确认、负数、错误地址、较弱随机和异常锚点原样保留，没有删样或事后换映射。

{stable}

共 {a['workers']} 个worker，累计 {a['worker_seconds']:.3f}/{a['worker_budget_seconds']} GPU-worker秒（含CPU准备与落盘）。开发计时 {a['timing_observations']['dev']} 条、独立确认 {a['timing_observations']['confirm']} 条；实际算子请求分别 {a['operator_requests']['dev']} 和 {a['operator_requests']['confirm']} 次。{a['numerical_checks']} 项数值检查、{a['graph_checks']} 项实际Graph核验通过，输入哈希跨进程/阶段不重合。数值包含随机、全零、单峰和极端有限logits，参考为FP64 Softmax；没有声称支持NaN/全负无穷输入。

memcheck/synccheck和定点racecheck通过；racecheck不独立证明全部全局内存并发正确性。采样温度{a['temperature_range_c'][0]}–{a['temperature_range_c'][1]}°C，100W上限及保护保持，未锁频、CPU未独占，桌面进程存在。

确认前的CPU核对发现开发与原计划确认种子会重叠，已在任何确认启动前把确认种子移到独立区间；原协议、新协议哈希和修正时刻保存在 `freeze/SEED_AMENDMENT.json`，全量哈希审计验证没有实际输入重叠。

保存了两次工程问题：最初源码生成误改到普通partial模板导致编译失败（未启动GPU）；首次sanitizer路径缺少注入库而退出，换成已有完整工具后通过。初版源码、错误日志和失败worker均保留，未记为成功样本。本轮确认完成后不追加映射或变体搜索。
'''
 (ROOT/'reports/REPORT.md').write_text(text)
 write(ROOT/'reports/RESULTS_COMPACT.json',dict(confirmation=results,development=dev,secondary_exploratory=secondary,baseline_consistency=aa,timing_sensitivity=timing,decision=read(ROOT/'derived/DECISION.json'),audit=a))
 print('REPORT_WRITTEN')
if __name__=='__main__':run()
