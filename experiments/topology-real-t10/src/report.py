from common import *
from selector import CHOICES
import numpy as np

def pct(x):return f'{x:+.3f}%'
def ci(v):return '['+', '.join(pct(x) for x in v)+']'
def table(rows,cols):
    return '\n'.join(['| '+' | '.join(t for t,k in cols)+' |','| '+' | '.join('---' for _ in cols)+' |']+['| '+' | '.join(str(r[k]) for t,k in cols)+' |' for r in rows])
def run():
    rows=read(ROOT/'derived/NET_RESULTS.json');a=read(ROOT/'derived/AUDIT.json');cal=read(ROOT/'derived/CALIBRATION.json');sels=read(ROOT/'derived/SELECTION_DIAGNOSTICS.json');static=read(ROOT/'freeze/STATIC.json');model=read(ROOT/'derived/MODEL_TRANSFER.json')
    main=[r for r in rows if r['primary']]
    def at(s,p,c,metric='outer_s',requests=1048576):return next(r for r in rows if r['scope']==s and r['candidate']==p and r['control']==c and r['metric']==metric and r['requests']==requests)
    gates={s:all(at(s,'TUNED',c)['ci_primary'][0]>0 for c in PROTOCOL['primary_comparators']['TUNED']) and at(s,'TUNED','TUNED_AA')['ci95'][0]<=0<=at(s,'TUNED','TUNED_AA')['ci95'][1] for s in PROTOCOL['scopes']}
    placegates={s:all(at(s,'PLACE_ONLY',c)['ci_primary'][0]>0 for c in PROTOCOL['primary_comparators']['PLACE_ONLY']) for s in PROTOCOL['scopes']}
    decision=dict(status='COMPLETED',new_baseline=54,new_baseline_plan=CHOICES[54],address_specific_gate=gates,placement_gate=placegates,
        default='BASE54 retained; any positive conditional result still requires independent replication',formal_kernel_sha256=PROTOCOL['baseline_hashes']['build/baseline/softmax_const.so'],no_outcomes_removed=True,
        interpretation='Conservative reading of frozen20 main contrasts, plus compatible-with-zero identical-parameter A/A for TUNED; not a new test or historical multiplicity adjustment. Address-specific prediction does not by itself identify a physical NUMA mechanism.')
    write(ROOT/'reports/DECISION.json',decision)
    intro='本轮仍未建立相对新基线的地址亲和稳定净加速。' if not any(gates.values()) and not any(placegates.values()) else '本轮存在通过所列保守比较门槛的条件性结果；应继续独立复验，不外推为普遍NUMA加速。'
    summary='\n'.join(f"- {s}：真实核采样选择TUNED相对新基线 {pct(at(s,'TUNED','BASE')['gain_pct'])}，99.75%区间 {ci(at(s,'TUNED','BASE')['ci_primary'])}，{at(s,'TUNED','BASE')['positive_processes']}/6进程为正；相对新开发静态规则 {pct(at(s,'TUNED','STATIC')['gain_pct'])}。" for s in PROTOCOL['scopes'])
    compact=[dict(scope=r['scope'],pair=r['candidate']+' / '+r['control'],gain=pct(r['gain_pct']),interval=ci(r['ci_primary']),positive=f"{r['positive_processes']}/6",gross=pct(r['gross_gain_pct'])) for r in main]
    costs=[];plans=[];aa=[];decomp=[];prefix=[]
    for s in PROTOCOL['scopes']:
        values=[r['setup_ms'] for r in cal if r['phase']=='confirm' and r['scope']==s and r['kind']=='calibration']
        costs.append(dict(scope=s,median=f'{np.median(values):.3f}',minimum=f'{min(values):.3f}',maximum=f'{max(values):.3f}',fallback=sum(r['fallback'] for r in sels if r['scope']==s)))
        for r in sels:
            if r['scope']==s:plans.append(dict(worker=r['worker'],scope=s,choice=r['choice'],offset=r['plan']['offset'],family=r['plan']['family'],fallback=r['fallback'],same=', '.join(k for k,v in r['same_as_tuned'].items() if v and k!='TUNED')))
        rr=at(s,'TUNED','TUNED_AA');aa.append(dict(scope=s,gain=pct(rr['gain_pct']),interval=ci(rr['ci95']),processes=', '.join(pct(v) for v in rr['process_gains_pct'])))
        for p in ['PAIR_ONLY','PLACE_ONLY','TUNED']:
            rr=at(s,p,'BASE');decomp.append(dict(scope=s,policy=p,gain=pct(rr['gain_pct']),interval=ci(rr['ci95']),candidate=f"{rr['candidate_with_setup_s']:.6f}",control=f"{rr['control_accounted_s']:.6f}"))
        rr=at(s,'TUNED','BASE',requests=262144);prefix.append(dict(scope=s,gain=pct(rr['gain_pct']),interval=ci(rr['ci95'])))
    sc=[r for r in read(ROOT/'derived/STATIC_CONTROLS.json') if r['requests']==1048576 and r['metric']=='outer_s']
    statictable=[dict(scope=r['scope'],policy=r['candidate'],gain=pct(r['gain_pct']),interval=ci(r['ci95']),positive=f"{r['positive_processes']}/6") for r in sc]
    diagnostic=[]
    for s in PROTOCOL['scopes']:
        for metric in ['outer_s','gpu_s','host_s']:
            rr=at(s,'TUNED','BASE',metric);diagnostic.append(dict(scope=s,metric=metric,gain=pct(rr['gain_pct']),interval=ci(rr['ci95']),processes=', '.join(pct(v) for v in rr['process_gains_pct'])))
    ledger=[json.loads(x) for x in (RUN/'ledger.jsonl').read_text().splitlines()];devcost=sum(x['worker_seconds'] for x in ledger if x['key'].startswith('dev_'))
    text=f'''# T10 真实核低成本采样与地址亲和实验

{intro}新基线为上轮热输入约+0.68%的固定规则：候选54，flags偏移17页、邮箱页17、RND07配对。正式原GPU二进制保持不变，SHA256 `{decision['formal_kernel_sha256']}`。

{summary}

本轮用真实完整Softmax筛选参数，取代上一轮预测力弱的通信代理。所有采样成本、失败回退成本和正式调度成本均收费；普通静态调优与当前分配地址的作用分开比较。

## 这轮实际得到的进展

新基线的固定收益得到了复验：相对旧同TPC规则，BASE54热输入约快0.832%、重写输入约快0.335%，两种条件均6/6为正（对既有LEGACY比较换方向表达，没有新增试验）。默认继续使用54。

在这个更强的基线上，TUNED热输入六次全部回退，未扣准备的平均速度比−0.004%，基本与基线相同；完整账单的−0.273%主要是校准费。重写输入三次改变选择、三次回退，未扣准备仍为−0.009%，完整净速度比−0.256%。因此不能仅靠假想更长摊销就声称能赚钱；本轮对BASE没有正的平均毛收益。准备中位费用分别17.563ms与25.933ms。

热输入TUNED相对新开发STATIC约+0.629%是保留的正结果，但STATIC本身比指定BASE慢约0.896%；胜过这个较慢对照不等于胜过新基线。重写输入STATIC比BASE约快0.063%，5/6为正，属于小幅静态调参的次要结果，尚无额外跨日复验；不提升为NUMA成功。A/A区间均含零，但这并不能消除全部状态偏差。

下一步更值得检验的是让少量采样承接真实请求，明确计入探索期间相对BASE的损失和更新成本，减少额外算子调用；同时把采样节奏与后续请求节奏对齐。它仍需相同预算的静态/错误地址/影子对照。若这些控制仍无改善，应把资源转向通信占比更高且工作区长期复用的LLM组件，而非在本条件下不断增加搜索直到出现正数。

## 新基线与硬件条件

BASE54在两种输入条件都作为新主基线；LEGACY11是原同TPC固定配对；FROZEN在热输入用54、重写输入用上一轮更强的56（offset17/page257/SAME_GPC），避免只与较弱参照比较。STATIC是本轮两个开发进程独立全算子数据选出的固定规则：{static['choices']}，其具体参数见冻结文件与 `selector.py`。STATIC的开发worker共耗时 {devcost:.3f} 秒，作为离线训练成本披露，不计入逐次部署费。

T10 TU102GL共有56个启用SM，物理GPC0–5分布10、12、12、10、0、12，每个worker均重新核验同版本驱动RM拓扑。原相邻偶奇配对28对全在同TPC；新基线RND07则是1对同TPC、7对同GPC不同TPC、20对跨GPC。因此新基线的小收益本身并不支持“越局部越快”；四种家族的全部配对和分组在 `FAMILY_TOPOLOGY.json`。当前实验改变配对和通信工作区地址，不改变SM屏蔽、频率设置、算子算法或GPU指令；也不从GPC编号推断物理距离。100W、风扇与过温保护保持，82°C停止阈值。

## 固定的低成本选择方法

候选16个：flags基址偏移0/17/67/131页 × 同TPC、同GPC不同TPC、跨GPC、基线RND07四种配对，邮箱页固定17。每次真实Graph调用包含32个完整Softmax，词表V=131072，56 cooperative CTA、128线程/CTA、48KiB共享内存、1CTA/SM。FROZEN56是额外强对照，不在16候选中。

1. 用编译后的CPU采样循环随机遍历16候选；每候选一次预热Graph、一次计时Graph，GPU event时间选出前三个非基线候选。
2. 前三名和BASE再随机做两轮复测；每轮每候选一次预热、两次正式Graph，取两次正式时间中位数。
3. 只有两轮都快于BASE且几何平均速度比超过+0.15%，才采用相应候选；否则退回BASE。多候选合格时选该得分最高者，固定索引打破平手。
4. 将选择装入同一个Graph并预热两次，形成可部署状态后停止准备计时。每次总58次Graph、1,856次完整算子调用，包括所有预热。随后保存选择，再进行完全分离的确认，不按确认数据重选。

采样只新增CPU端批量调度代码；配对224字节、flags指针、页号由Graph参数传入。每次更新读回核参数，核验Graph executable/stream/events保持不变。原核工作分配也保持：SM0–15各处理2432元素，SM16–55各处理2304元素；不同配对可能改变等待不均衡工作完成的方式，因此单纯配对收益仍不能独立证明更短的物理通信延迟。准备费涵盖参数表构造、随机计划、全部采样更新/执行、计时数组、拟合及最后装载/预热；common Graph构建、输入分配、上下文/编译不计费。额外研究数值检查、SHADOW准备和日志落盘也不计入目标部署费，其执行与原始记录保留。正式块仍实测参数更新、2次conditioning Graph、同步和结果提取的完整墙钟。计时事件查询与测量包装也在账单内，对各方案相同；这是可复算的测量驱动请求块，不是完整线上LLM服务。退回BASE也支付已发生的校准费。

## 对照和统计

TUNED使用本工作区的选择；TUNED_AA使用完全相同参数和相同准备费。PAIR_ONLY只改配对，PLACE_ONLY只改偏移，均从筛选数据取得，属于较弱的分解选择器，收费仍保守地扣完整实测准备费。WRONG在相邻偏移处选择家族，却部署于TUNED选择的偏移；POOL平均各偏移家族成本，再部署于TUNED偏移。SHADOW用相同输入、输出、原核、同一个Graph，在另一flags分配上按完全相同方法学习，再把完整选择转回目标。SHADOW不同虚拟地址不证明物理L2分区不同。对照可能选中相同参数，按真实选择保留。

2个开发、6个确认进程；不同种子共32个输入哈希。短测试轮转4输入；长测试使用每进程slot0。batch每Graph连续32次完整算子；freshbatch每次算子前复制固定输入，复制计时。不是整模型推理，也不是每请求生成新logits。每方案/条件/确认进程1,048,576请求，16块，11方案随机顺序；262,144前缀仅作预先声明的次要摊销观察。

主指标为外层墙钟，加候选实测准备费；比较方准备费免费，除同参数TUNED_AA同等收费。主统计单位6进程，速度比为 `100×(对照时间/候选时间−1)` 的进程几何平均；正数快，不能当成同百分比耗时下降。精确枚举6^6种经验进程bootstrap，20个冻结主比较用99.75%区间，95%区间作描述。未校正整个历史项目所有尝试；六进程不替代跨日期/重启/多卡验证。

## 主结果

{table(compact,[('输入','scope'),('候选 / 对照','pair'),('含准备净速度比','gain'),('99.75% 区间','interval'),('正向进程','positive'),('未扣准备','gross')])}

所有正式数据均保留，包括长等待和负结果。未因结果好坏更换参数、删点、补跑或改变主指标。只在单个条件胜过BASE不足以证明地址亲和；还须相对STATIC/FROZEN及错误/混合/独立分配规则获得优势，并检查同参数对照。

## 准备成本与选择

{table(costs,[('输入','scope'),('准备中位ms','median'),('最小ms','minimum'),('最大ms','maximum'),('回退次数/6','fallback')])}

{table(plans,[('进程','worker'),('输入','scope'),('候选','choice'),('偏移页','offset'),('配对','family'),('回退','fallback'),('同参数标签','same')])}

以下分解均相对BASE，95%描述性区间。PAIR_ONLY并未另做独立两轮精炼，不把其弱表现当成配对不可优化的证明。秒数是1,048,576请求每进程账单算术平均，与对数速度比统计不同。

{table(decomp,[('输入','scope'),('候选','policy'),('净速度比','gain'),('95% 区间','interval'),('候选含准备秒','candidate'),('BASE秒','control')])}

## 同参数与静态对照

{table(aa,[('输入','scope'),('TUNED / TUNED_AA','gain'),('95% 区间','interval'),('逐进程速度比','processes')])}

A/A非零不能归因于拓扑，仍可能有提交顺序、系统等待与热状态波动；即便同参数区间跨零也不能保证其他比较完全无偏。

{table(statictable,[('输入','scope'),('静态候选 / BASE','policy'),('速度比','gain'),('95% 区间','interval'),('正向进程','positive')])}

STATIC若获益只是固定调参的次要结果；开发成本已经披露，不能把它当成当前地址感知因果成功。LEGACY比较也能检查上轮+0.68%是否在本轮仍成立，不能预设历史改善必然保留。

## 辅助计时与摊销

GPU/host replay指标再加实测更新费和候选准备费；外层本已包含更新，未重复扣除。计时长尾在 `TIMING_TAILS.json` 全面记录，不删除。host减event仅为两个区间的差，不是单独测出的CPU执行时间；没有系统调度trace，不能对后台进程定责。

{table(diagnostic,[('输入','scope'),('口径','metric'),('TUNED / BASE','gain'),('95% 区间','interval'),('逐进程','processes')])}

262,144请求前缀（同一次运行的前4块，非独立复验）：

{table(prefix,[('输入','scope'),('净速度比','gain'),('95% 区间','interval')])}

`AMORTIZATION.json`只用完整长测原始时间估算在性能不变假设下的收支平衡请求数；无正毛收益则无有限平衡点。这种外推不是实测更长寿命，也不替代主测试。

## 低成本采样能否预测后续真实核

只在开发集，对16候选的低预算真实核筛选时间与独立后续全算子时间比较；正式确认不据此改选择。

{table([dict(worker=r['worker'],scope=r['scope'],pearson=f"{r['pearson']:.3f}",spearman=f"{r['spearman']:.3f}") for r in model],[('进程','worker'),('输入','scope'),('Pearson','pearson'),('Spearman','spearman')])}

真实核消除了synthetic tail在广播读流量、指令和到达模型上的失真，但少量样本仍会受GPU状态/缓存/次序波动影响，筛选与长串执行的节奏不同。16候选搜索不代表穷尽全部配对和地址；flags偏移共同移动邮箱与控制行，无法分别识别L2归属、缓存冲突、全局计数争用和裸SM距离。更换配对还会改变局部归约的浮点组合顺序；数值检查通过不等于已经单独识别通信机制。PLACE_ONLY固定配对，提供更接近纯地址放置的分解，但仍有筛选预算与收费口径限制。

## 审计与复现

运行 `{RUN.name}`；{a['workers']}个worker全部完成，{a['worker_seconds']:.3f}/{a['budget_seconds']} worker秒。{a['numerical_checks']:,}项数值检查通过；{a['calibration_runs']}次校准共{a['calibration_operator_calls']:,}次算子（含资格/影子，不全收进目标账单）；{a['graph_dags_checked']}张Graph顺序核验；短测{a['short_observations']:,}条计时，其中正式{a['short_test_observations']:,}条；长测{a['net_operator_requests']:,}正式请求和{a['net_conditioning_requests']:,}预热请求。请求数不代表独立样本数。数值检查在各方案块前后和长测后执行，不声称每次请求输出都被逐个检查。

memcheck/synccheck资格检查通过；racecheck定点覆盖原paired核1个launch，不是整轮全量覆盖。没有新GPU代码。温度{a['temperature_min']}–{a['temperature_max']}°C，100W保持；未锁频、桌面进程仍存在，残余系统波动必须结合A/A与计时长尾判断。

全部GPU worker完成后，首次CPU汇总因NumPy布尔值不能直接写JSON而失败。原 `analyze.py` 和错误日志保持不变，另加 `analyze_repaired.py` 只在序列化边界转成原生标量；统计公式、冻结选择和原始数据未改，没有重跑GPU。修复记录见 `ENGINEERING_NOTES.json`。

完整包提供冻结协议/源码哈希、构建命令、原核二进制、全部原始数据、逐进程数值与遥测。按根目录 `README_REPRODUCE.md` 在无GPU环境重算派生结果；小包用于评审，不包含原始数据。默认BASE54保留；当前结果不凭小正数或更长假想摊销宣布NUMA目标完成。
'''
    (ROOT/'reports/REPORT.md').write_text(text)
    (ROOT/'reports/REVIEW_QUESTIONS.md').write_text('''# T10 真实核采样实验复核问题

1. 上轮+0.68%的BASE54在本轮相对LEGACY是否仍成立？freshbatch是否同时胜过上一轮更强的FROZEN56？
2. 16候选包含4偏移×4配对，缩小搜索减少了成本，也可能丢掉最优点。只能评价本选择器，不能否定全部地址亲和空间。
3. 筛选一次、精炼两轮能否稳定区分0.1%量级差异？0.15%门槛是预设部署规则，不是统计显著性阈值。
4. 每次校准1,856真实算子和参数更新均计入吗？退回BASE仍付费吗？是否把共同构图、输入分配、研究I/O正确区分？
5. 真实核短采样与长串请求在热状态、时钟、缓存状态和系统等待上是否仍有差异？开发集独立排序相关性如何？
6. 地址特异性证据应来自目标工作区胜过SHADOW/WRONG/POOL，而不只是胜过BASE。SHADOW用了同输入同Graph仅换flags，但VA变化不证明物理内存分区变化。
7. WRONG/POOL仍共享TUNED的偏移，不是完全独立地址对照；相同选择的次数必须披露，不能强制改坏对照。
8. PAIR_ONLY/PLACE_ONLY只用筛选分数，没有TUNED精炼，仍扣完整校准费；分解结果的限制是否明确？
9. TUNED_AA参数和准备费相同。若A/A出现小偏差，是否谨慎解释同量级收益？所有主机/GPU长尾是否原样保留？
10. STATIC利用开发全算子数据，在线不校准；离线成本已披露。静态规则获益不等于当前地址感知或CPU式NUMA机制。
11. 6进程是统计样本；20比较校正不覆盖历史所有试验。固定输入重复、slot0长测和缺少跨日复验如何限制LLM泛化？
12. 是否只以全1,048,576请求外层净时间作为本轮主结果，保留262,144前缀为次要分析，不根据结果选择更有利寿命？
''')
    print('REPORT COMPLETE',decision)
if __name__=='__main__':run()
