"""Render the completed experiment, including unfavorable and null outcomes."""
from common import *
import numpy as np
import pandas as pd

def signed(x):return f'{x:+.3f}%'
def span(x):return '['+', '.join(signed(v) for v in x)+']'
def table(rows,cols):
    return '\n'.join(['| '+' | '.join(t for t,k in cols)+' |','| '+' | '.join('---' for _ in cols)+' |']+['| '+' | '.join(str(r[k]) for t,k in cols)+' |' for r in rows])
def run():
    result=read(ROOT/'derived/NET_RESULTS.json');audit=read(ROOT/'derived/AUDIT.json')
    outer=[r for r in result if r['metric']=='outer_s']
    primary=[r for r in outer if r['primary']]
    short=read(ROOT/'derived/SHORT_RESULTS.json');micro=read(ROOT/'derived/MICRO_VALIDATION.json')
    plans=read(ROOT/'derived/SELECTED_PLANS.json');confirm=[r for r in plans if r['phase']=='confirm']
    model=read(ROOT/'derived/MODEL_TRANSFER.json');static=read(ROOT/'derived/STATIC_RULE_TRANSFER.json')
    ledger=[json.loads(s) for s in (RUN/'ledger.jsonl').read_text().splitlines()]
    devcost=sum(r['worker_seconds'] for r in ledger if r['key'].startswith('dev_'))
    def at(scope,p,c):return next(r for r in outer if r['scope']==scope and r['candidate']==p and r['control']==c)
    gates={s:all(at(s,'JOINT',c)['ci_primary'][0]>0 for c in ['IDENTITY','BLIND','WRONG','POOL','SHADOW']) and at(s,'JOINT','JOINT_AA')['ci95'][0]<=0<=at(s,'JOINT','JOINT_AA')['ci95'][1] for s in PROTOCOL['scopes']}
    placegates={s:all(at(s,'PLACE_ONLY',c)['ci_primary'][0]>0 for c in ['IDENTITY','BLIND','SHADOW']) for s in PROTOCOL['scopes']}
    decision=dict(status='COMPLETED',address_specific_net_gain_gate=gates,placement_gate=placegates,
        default='IDENTITY retained pending independent replication' if any(gates.values()) or any(placegates.values()) else 'IDENTITY retained; this experiment does not establish address-specific net acceleration',
        gate_interpretation='Descriptive conservative reading of frozen primary contrasts: all indicated adjusted intervals positive, and JOINT identical-parameter A/A interval compatible with zero. Not a new statistical test or historical multiplicity correction.',
        formal_kernel_sha256=PROTOCOL['baseline_hashes']['build/baseline/softmax_const.so'],all_outcomes_retained=True)
    write(ROOT/'reports/DECISION.json',decision)
    compact=[]
    for r in primary:
        compact.append(dict(scope=r['scope'],contrast=r['candidate']+' / '+r['control'],gain=signed(r['gain_pct']),ci=span(r['ci_primary']),positive=f"{r['positive_processes']}/6",gross=signed(r['gross_gain_pct'])))
    main=table(compact,[('输入','scope'),('候选 / 对照','contrast'),('含校准净速度比','gain'),('99.6875% 区间','ci'),('正向进程','positive'),('未扣校准','gross')])
    decomposition=[]
    for s in PROTOCOL['scopes']:
        for p in ['PAIR_ONLY','PLACE_ONLY','JOINT']:
            r=at(s,p,'IDENTITY');decomposition.append(dict(scope=s,policy=p,gain=signed(r['gain_pct']),ci=span(r['ci95']),candidate=f"{r['candidate_with_setup_s']:.6f}",control=f"{r['control_accounted_s']:.6f}"))
    staticrows=[dict(scope=r['scope'],gain=signed(r['gain_pct']),ci=span(r['ci95']),positive=f"{r['positive_processes']}/6") for r in static if r['metric']=='outer_s']
    aarows=[dict(scope=s,gain=signed(at(s,'JOINT','JOINT_AA')['gain_pct']),ci=span(at(s,'JOINT','JOINT_AA')['ci95'])) for s in PROTOCOL['scopes']]
    setup=[];dup=[];microrows=[]
    for s in PROTOCOL['scopes']:
        ss=[r for r in confirm if r['scope']==s];v=[r['setup_ms'] for r in ss]
        setup.append(dict(scope=s,median=f'{np.median(v):.3f}',minimum=f'{min(v):.3f}',maximum=f'{max(v):.3f}'))
        for c in ['IDENTITY','PAIR_ONLY','PLACE_ONLY','WRONG','POOL','SHADOW','BLIND']:
            dup.append(dict(scope=s,control=c,count=sum(r['mapping']['JOINT']['index']==(read(ROOT/'freeze/BLIND_BEST.json')['choices'][s] if c=='BLIND' else r['mapping'][c]['index']) for r in ss)))
        for p in ['JOINT','PAIR_ONLY','PLACE_ONLY','SHADOW']:
            vv=[r['validation_vs_identity_pct'] for r in micro if r['phase']=='confirm' and r['scope']==s and r['policy']==p]
            microrows.append(dict(scope=s,policy=p,median=signed(float(np.median(vv))),minimum=signed(min(vv)),maximum=signed(max(vv))))
    intro='本轮没有证明地址亲和调度本身的稳定净加速。' if not any(gates.values()) and not any(placegates.values()) else '本轮出现通过所列保守比较门槛的条件性结果；仍需跨日期独立复现，不能外推为一般 NUMA 加速。'
    bullets='\n'.join(f"- {s}：JOINT 相对原快核 {signed(at(s,'JOINT','IDENTITY')['gain_pct'])}，相对开发集最强固定规则 {signed(at(s,'JOINT','BLIND')['gain_pct'])}；同参数 A/A 为 {signed(at(s,'JOINT','JOINT_AA')['gain_pct'])}。" for s in PROTOCOL['scopes'])
    text=f'''# T10 完整通信尾部与地址放置实验

运行：`{RUN.name}`。{intro}默认快核与原配对保留。

{bullets}

这一轮检验的具体变化是：不再只拿两 SM 的邮箱往返选配对，而是把 28 对归并、共同原子计数、最后到达者汇总、向所有 SM 广播放在同一微测中。候选同时改变配对、邮箱页和整个 flags 工作区偏移，再将参数放回原来完整 Softmax。正式测速二进制逐字节不变，SHA256：`{decision['formal_kernel_sha256']}`。没有把换算法或更快编译代码算作拓扑收益。

## 已知硬件事实与边界

同版本驱动 RM 查询每个 worker 都重新核验。物理 GPC0–5 启用 SM 为 **10、12、12、10、0、12**，共 56；原始相邻偶奇配对 28 对全属同 TPC。先前独立实验在页17测得孤立邮箱 RTT：同 TPC1160.6ns、同 GPC 不同 TPC1178.9ns、跨 GPC1174.3ns。这是完整同步往返，不能当成单程连线延迟；GPC 编号也不是物理平面坐标。此前并发时偏好可反转，尚无稳定 GPC NUMA 域证据。本轮不重复生成这些历史测量，包中包含当前驱动拓扑与查询来源，历史性能原始数据在前一交付包。

## 固定实验设计

- 完整 Softmax，词表 V=131072，56 个 cooperative CTA，每个128线程、48KiB共享内存，1 CTA/SM。数据分工、last-arriver collector 与原核一致。
- `batch`：每个 Graph 连续32次完整 Softmax。`freshbatch`：每次 Softmax 前复制输入，再连续32次；复制成本计入。内容来自固定输入环，**不是完整 LLM 推理，也不是每请求新生成的 logits**。
- 地址偏移 0/17/67/131 页 × 邮箱页 0/17/257 × 11种配对，共132候选；11种包括原同TPC、同GPC不同TPC、跨GPC与8种固定随机。只从这个有限候选集选择，没有穷尽全部排列。
- 每次新分配先用独立带计时的 Softmax 采16次到达差，再做12轮通信微测。按前6轮与后6轮中位数的较大者选参，保存选择后才进行8轮留出验证。独立工作区再训练 SHADOW。微测、留出结果和确认算子结果均不反向改选择。
- 2个开发进程仅用于选择 BLIND 最强静态规则；6个确认进程固定执行。BLIND 在确认开始前冻结：batch候选54（offset17/page17/RND07），freshbatch候选56（offset17/page257/SAME_GPC）。
- 正式长测试：每方案、每输入条件、每确认进程1,048,576次请求，16个随机顺序块；每块还执行2次预热 Graph。全部预热和每次参数更新均计入外层墙钟。正式长测试使用该进程输入slot0；短测试轮转4个输入slot。不能把上亿次请求视为上亿独立样本，统计单位是6个进程。
- 同输入slot所有方案共用 Graph executable、stream与events；每次更新读回核参数并核验 handles 不变。更新只有224字节配对表、flags指针、页号，未在热核中新增调度指令。

## 主结果：真实请求账单

速度比定义 `100×(对照时间/候选时间−1)`，正数表示候选更快，不等同于相同百分比的耗时下降。以下为6进程速度比的几何平均。每个候选支付实测完整校准；对照免费获得自身选择，是偏保守的比较。主指标是请求块外层墙钟，GPU event 和 host replay 仅作诊断。

{main}

16个预先列出的主比较使用99.6875%区间（Bonferroni16）；区间通过6^6种经验进程重采样精确枚举。它们不是六次进程足以证明普遍规律的保证，也未校正整个历史项目的所有尝试。全部95%区间、逐进程结果、短测试、GPU/host指标见 `derived/`；不能从其中事后挑一个窗口替代主结论。

## 分解：只改配对、只改地址、共同改变

下表仍给每种候选扣同一次完整校准，未虚构更便宜的子集校准。PAIR_ONLY 属探索性比较。秒数为每进程完整1,048,576请求账单的算术平均，速度比统计则按进程对数计算。

{table(decomposition,[('输入','scope'),('候选','policy'),('净速度比','gain'),('95% 区间','ci'),('候选含准备秒','candidate'),('原核秒','control')])}

## 为什么 freshbatch 的平均小正数不能当成成功

freshbatch 的 JOINT/IDENTITY 六进程净速度比分别约 −0.176%、−0.816%、+4.535%、−0.257%、−0.674%、−0.862%。平均+0.274%主要被confirm_2拉起。该进程原配对某次Graph在GPU event内约0.309ms，host计时却达99.164ms；另一次也同时出现约21.294ms的GPU event长尾。没有系统调度追踪，不能给具体后台进程定责，也不能把所有长尾归为同一原因。**所有这些观测原样计入主结果，没有删除、替换或补跑。** 全108个方案/进程/条件的尾部明细在 `derived/TIMING_TAILS.json`，这是看完结果后的描述性检查。

按辅助GPU event口径并同样扣校准/更新，JOINT在freshbatch相对原配对为−0.593%，六进程全负。BLIND固定规则的freshbatch外层平均+1.081%也受上述原配对长尾放大；其GPU口径为+0.216%，六进程全正，外层逐进程中5个约+0.123%至+0.370%、1个+5.450%。热输入BLIND外层+0.677%，六进程全正，是较一致的小幅静态调参收益；其离线选择成本和缺少跨日期复验仍需披露。它可作为下一轮强对照，但不是当前地址亲和因果主张的成功。

## 固定规则及同参数对照

BLIND 是两次开发完整算子测量选出的固定规则，确认时不校准。这些结果是次要静态调参结果，不可归因于每次新地址的感知。其开发worker共耗时 {devcost:.3f} 秒（包含开发流程的微测与记录），没有计入每次部署的在线账单；不代表任何场景都能免费学习。

{table(staticrows,[('输入','scope'),('BLIND / 原配对','gain'),('95% 区间','ci'),('正向进程','positive')])}

JOINT_AA 与 JOINT 的配对、flags指针、页号完全相同，也被扣相同准备费。以下偏差帮助判断次序/波动尺度，不能解释为 NUMA 效应。热输入A/A为+0.064%，95%区间[+0.004%,+0.132%]未含零，说明同参数比较仍存在小幅残余偏差，尤其不能把同一量级的小正数轻率当作机制收益。

{table(aarows,[('输入','scope'),('JOINT / JOINT_AA','gain'),('95% 区间','ci')])}

WRONG 与 POOL 只破坏家族选择规则、仍共享 JOINT 选出的放置；SHADOW 才从另一虚拟地址分配学习完整选择。它们有时自然选中相同参数，不能强制换成不同参数来制造差异。六个确认进程中与 JOINT 完全相同的次数：

{table(dup,[('输入','scope'),('对照','control'),('相同次数/6','count')])}

## 微测是否能预测完整算子

通信微测的留出表现如下，数值为各进程“原始配对通信时间/所选通信时间”的速度比；这里没有完整 Softmax 计算与输出，也没有部署校准账单，因此不能称为算子净加速。

{table(microrows,[('输入','scope'),('选择','policy'),('六进程中位','median'),('最小','minimum'),('最大','maximum')])}

只在开发集对全部132个候选比较微测留出值与完整算子时间，得到以下相关系数。较低相关性意味着当前通信模型难以给实际算子可靠排序。此分析是描述性诊断，没有据此重选任何确认参数。

{table([dict(worker=r['worker'],scope=r['scope'],pearson=f"{r['pearson']:.3f}",spearman=f"{r['spearman']:.3f}") for r in model],[('进程','worker'),('输入','scope'),('Pearson','pearson'),('Spearman','spearman')])}

限制：本轮开发集记录的时间戳差均落在32ns网格上（原始记录差值GCD；不是硬件精度的普遍保证），因此不能把数ns的拟合差当作已分辨的单次延迟。到达模型用各SM自己的局部时长差，未精确重现共同时间轴上的屏障释放差。带时间戳诊断核的寄存器和访存行为也不同于正式原核。synthetic tail复制主要配对、归并与flag广播依赖，却不复制真实计算产生的全部缓存/流水线状态；微测每SM只有thread0读控制结果，正式原核在CTA同步后128线程都会读取控制结果并输出，所以它并非完全相同的广播读流量。此差异是未隔离的模型限制，不能事后断言它已解释结果。微测记录在最终屏障后写出，但计时指令本身仍会扰动执行。flags偏移同时移动邮箱和公共控制，不单独定位哪个地址造成收益；虚拟地址不同不证明物理内存分区不同。

## 成本与审计

真正可部署的准备计时从诊断剖析开始，到训练、下载、验证记录结构、拟合、生成可用参数为止。留出验证、SHADOW校准和研究落盘不收进候选部署费，它们各自原始记录保留。所有正式请求块包含 Python/Ctypes参数包装、Graph更新核验、2次预热、同步和返回计时数组；数组实际分配/复制包含在外层墙钟中。共同Graph创建、首次CUDA上下文/编译、输入分配、块间研究文件写出不计入请求账单，故不是完整在线服务启动耗时。

{table(setup,[('输入','scope'),('准备中位ms','median'),('最小ms','minimum'),('最大ms','maximum')])}

审计：{audit['workers']}个worker记录，{audit['completed_workers']}完成；实测已知worker时间 {audit['measured_worker_seconds']:.3f} 秒，加中断worker保守记账240秒，总预算账 {audit['budget_charge_seconds']:.3f}/{audit['budget_seconds']}秒。中断worker实际结束时刻未知，240秒只用于预算，不能称实测GPU时长。

数值检查 {audit['numerical_checks']:,} 项；通信微测 {audit['micro_launches']:,} 次、{audit['micro_sm_records']:,} 条SM记录；{audit['graphs_checked']}张Graph核验；32个独立输入哈希；短测试 {audit['short_observations']:,} 条观测（其中正式 {audit['short_test_observations']:,}）；长测试 {audit['net_operator_requests']:,} 次正式请求及 {audit['net_conditioning_requests']:,} 次预热请求。数值检查在每方案正式块前后和长测试结束后执行，不声称逐次检查每个请求。温度 {audit['temperature_min']}–{audit['temperature_max']}°C，100W上限和风扇/过温保护保持，停止阈值82°C。没有锁时钟，桌面进程仍存在；随机块顺序和A/A用于量化残余波动，不能声称完全隔离硬件。

初期失败全部保留：①诊断CPU数组16×448缺reshape，qualification失败，未进入正式开发；②memcheck扩大到达差，触发普通10us host guard，工具本身0内存错误但该worker失败，随后仅sanitizer路径合成延迟上限5us，普通实验不变；③完整racecheck被轮次中断，无完成摘要，记为INTERRUPTED_UNCONFIRMED。恢复后对新tail核单次定点racecheck通过，**不是整个campaign全量racecheck通过**；memcheck_v3/synccheck_v3完整资格检查通过，正式旧二进制的前期检查沿用历史证据。初版源码、修复版、日志、未完成数据均留在包中，没有静默删去失败。

## 下一步与论文表述

可以写为：真实屏蔽拓扑存在非均匀性，但“同TPC单独通信略快”与“完整算子可净加速”是两条不同证据链；并发、全局归并、地址放置和提交节奏会改变排序。这轮的完整尾部模型让因果对照更接近实际，仍应以主比较结果为准。

如果继续投入，优先检验两项可证伪假设：一是在真实快核中以少量实际请求采样校准后冻结选择，和相同采样预算的静态/随机搜索比较，以隔离代理模型失真；二是寻找跨CTA通信占比更高、重复使用同一工作区的LLM归约组件，再比较原配对与地址感知选择。两者都要先算收支平衡，不以更多搜索直到出现正数为目标。此报告不把静态调参、微测收益或置信区间跨零的小正数包装为已经实现NUMA净加速。

## 文件与复现

完整报告旁有 `REVIEW_QUESTIONS.md`、图、机器判定 `DECISION.json`；冻结协议/实现/BLIND在 `freeze/`，全部原始数据和失败记录在 `runs/{RUN.name}/`。按根目录 `README_REPRODUCE.md` 进行不调用GPU的重算；小包只供评审，独立复算需要完整包。
'''
    (ROOT/'reports/REPORT.md').write_text(text)
    (ROOT/'reports/REVIEW_QUESTIONS.md').write_text('''# 外部复核与质疑清单

请首先核对主指标outer_s及全部对照，不根据某个微测或GPU event小正数判成功。欢迎明确指出方法失败，不能以寻求正结果为由忽略反例。

1. 真实驱动拓扑是否足以支持“GPC局部NUMA域”？已有同GPC不同TPC不优于跨GPC的反例，原配对已全同TPC。
2. 带计时诊断核与正式原核不同，synthetic tail仅thread0读取控制结果而正式核为整个CTA读取；局部时长差和synthetic tail是否错误重现真实到达/缓存/广播流量？开发集132候选相关性能否证实模型有用？
3. 微测训练12轮、留出8轮，在132候选上极值选择仍会过拟合。留出不反馈选参是必要但不足的条件；六进程独立性与跨日期外推应如何加强？
4. 指针偏移同时移动控制与邮箱，不能独立识别L2归属、缓存组冲突、控制行争用和SM距离。VA不同也不等于物理分区不同。
5. WRONG/POOL在JOINT放置上测试，只是家族选择干预；相同选择有多少？SHADOW完整换分配是否能更有效排除普通调参？
6. JOINT_AA若非零，应先解释同参数偏差，不能归因于拓扑。桌面负载、未锁时钟、热状态、Graph参数更新与次序残留仍需控制。
7. BLIND用了两个开发进程的完整算子数据，在线不收费但开发成本已披露。若其更快，是否说明静态调参比当前地址模型更实用，而非NUMA亲和胜出？
8. 主账单含校准、每块更新、预热、同步、包装/输出数组，排除共同构图/分配/编译及研究I/O。固定1024K请求的摊销是否匹配预期部署寿命？
9. freshbatch只是复制固定向量，并非上游真实decoder。输入仅slot0用于长测，更多输入用于短测与资格检查。何种真实LLM组件能带来更可信的泛化？
10. 6进程经验bootstrap不能替代跨日/重启/多卡复现，Bonferroni只覆盖本轮16主对比，不覆盖历史所有试验。是否需要预注册更长的最终验证？
11. 全量racecheck中断不能记成通过；本轮只定点检查1个新tail launch，mem/sync完整资格通过。如何评价剩余覆盖缺口？
12. 即使某项局部微测更快，是否在同一完整原核、同一Graph及完整成本后仍胜原配对、BLIND、错误选择、混合选择、独立分配选择？若没有，不应声称已完成目标。
''')
    print('REPORT WRITTEN',decision)
if __name__=='__main__':run()
