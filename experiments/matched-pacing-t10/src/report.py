from common import *
import statistics,math
r=runroot();d=read(r/'derived/results.json');a=read(ROOT/'reports/FINAL_AUDIT.json');p=read(ROOT/'freeze/PROTOCOL.json');blocks=d['blocks'];groups=d['groups'];assert d['formal_complete'], 'Do not claim fourblock completion for partialcampaign'
def pct(x):return f'{100*(x-1):+.2f}%'
net=[b['throughput_ratio'] for b in blocks]
if all(x>1 for x in net):finding='本轮四块均观察到净吞吐收益，但只覆盖当前固定准备流程和同一输入，不能据此宣称跨运行状态的稳定优化。'
elif all(x<1 for x in net):finding='本轮四块均未观察到净吞吐收益。短暂停顿是否缩短单次处理，与把等待算进去后是否获益，是两个独立需要报告的问题。'
else:finding='本轮在统一准备流程后仍有收益方向不一致，尚不能把短暂停顿当作稳定提速方案。'
text=['# T10 统一准备流程下的请求节奏复验','',f'run `{r.name}`；2026-10-17。上一轮收益主块+20.67%、辅助确认-5.95%，本轮专门缩小准备条件差异，检查1Hz/20Hz监测条件下的A/B结果。','',finding,
 f"四个进程各先固定空闲180秒，随后30秒连续提交conditioning，测量A→B→A→B→A，各8秒。监测频率顺序1/20/20/1Hz；所有进程shape={p['shape']}、seed={p['seed']}、四槽输入与权重哈希相同。使用前轮完全相同的backend.so/cubin和宿主state_run；没有重新编译数学程序。",
 f"实际worker启动温度依次为{[w['worker_start_temperature'] for w in d['workers'] if w['kind']=='matched']}°C。流程相同不等于硬件状态完全相同；残留温度差异与整卡历史仍限制监测频率的因果解释。",
 f"本轮加间隔B的逐进程完整周期仅{min(x['B_cycle_us'] for x in blocks):.2f}–{max(x['B_cycle_us'] for x in blocks):.2f}us，连续提交A参照为{min(x['A_cycle_us'] for x in blocks):.2f}–{max(x['A_cycle_us'] for x in blocks):.2f}us。四块单请求ready汇总变化{pct(d['all_blocks_summary']['ready_ratio'])}，但包含等待的完成率变化{pct(d['all_blocks_summary']['throughput_ratio'])}；等待成本超过了本轮省下的处理时间。",
 'A=连续READY0；B=输出完成、读完事件后请求sleep100us。实际间隔和完整阶段墙钟均保留，不用名义100us替代实测成本。',
 '|块|监测|连续提交参照周期us|加间隔总周期us|单请求ready变化|完成率变化|','|---|---:|---:|---:|---:|---:|']
for b in blocks:text.append(f"|{b['block']}|{b['monitor_hz']}Hz|{b['A_cycle_us']:.2f}|{b['B_cycle_us']:.2f}|{pct(b['ready_ratio'])}|{pct(b['throughput_ratio'])}|")
text+=['','每次B以相邻两段A的几何均值作参照，两次B比较再汇总成一个进程结果。周期/比值使用一致的几何均值口径；两个B共享中间A，不算两个独立进程。','',
 '|监测层|进程数|A总周期us|B总周期us|ready变化|完成率变化|','|---|---:|---:|---:|---:|---:|']
for g in groups:text.append(f"|{g['monitor_hz']}Hz|{len(g['blocks'])}|{g['A_cycle_us']:.2f}|{g['B_cycle_us']:.2f}|{pct(g['ready_ratio'])}|{pct(g['throughput_ratio'])}|")
text+=['','每个监测层只有两个进程，不给请求级显著性或置信区间，不把几十万相关请求当作独立样本。',
 '![完整周期与净收益](figures/02_wall_time_and_net_gain.png)','',
 '## 这一轮能比较什么','',
 '本轮新四块之间统一了输入、空闲时长、预热时长、阶段时长与A/B顺序，指定改变的因素是监测频率。实际温度、设备残留状态和时间顺序仍可能有差异，以下完整报告。固定空闲180秒不是保证所有隐藏状态已复位；没有根据温度阈值延长等待，也没有按跑分快慢筛选。',
 '它不是旧七段协议的原样复现：旧主块还包含1000us间隔C和BURST64的D，且没有每块相同的180秒空闲准备。本轮去掉C/D，集中看A/B。因此新旧收益差不能单独归因于监测频率；当前四块之间的比较才是监测条件的有限对照。',
 '“独立进程”描述进程重建，不意味着整卡热历史、其他客户端或所有硬件状态统计独立。ABBA顺序减少简单顺序偏差，不能保证消除它。',
 '## 原始阶段与返回参照','',
 '|块|B阶段|前A周期us|B周期us|后A周期us|B完成率变化|返回A周期变化|','|---|---:|---:|---:|---:|---:|---:|']
for x in d['contrasts']:text.append(f"|{x['block']}|{x['B_phase']}|{x['before_A_cycle_us']:.2f}|{x['B_cycle_us']:.2f}|{x['after_A_cycle_us']:.2f}|{pct(x['B_throughput_over_bracket_A'])}|{pct(x['return_A_over_before_A'])}|")
text+=['','![逐时间轨迹](figures/01_matched_timelines.png)','','![返回前后与完整周期](figures/04_bracket_and_return.png)','',
 '本轮A阶段均值约381–443us，每阶段超过850us的请求比例不超过0.11%，没有充分复现旧实验中大量约970–1000us请求构成的慢态。因此四块净收益为负并不等于已经解释或消除了旧跳变；它只是再次表明，在较快基线下固定暂停成本不划算。',
 '所有conditioning和正式阶段的请求均保存。100ms桶仅作描述，未丢弃开头或异常点；时钟图只画真实包含在桶内的查询，不补插值。650/850us快慢描述沿用前轮界线，不用于筛选、检验或调度。','',
 '## 准备流程、温度与观察成本','',
 '|块|监测|实际空闲s|worker启动温度°C|worker温度范围°C|空闲结束到conditioning开始ms|NVML平均查询耗时ms|','|---|---:|---:|---:|---|---:|---:|']
for w in d['workers']:
 if w['kind']=='matched':text.append(f"|{w['block']}|{w['monitor_hz']}Hz|{w['preparation']['actual_s']:.3f}|{w['worker_start_temperature']}|{w['temperature_range']}|{w['idle_end_to_condition_start_ms']:.1f}|{w['poll_ms']['mean']:.2f}|")
text+=['','空闲准备只运行CPU/NVML读取，不创建CUDA上下文、不占用GPU-worker锁，因此单列墙钟时间；worker内部的初始化、数值验证、conditioning、测量和导出全部计入GPU-worker账本。',
 '20Hz条件仅密集读SM时钟/降频原因，完整功耗温度计数约1Hz；1Hz条件只做完整查询。监测频率在启动遥测进程前设置，整个worker保持一致，阶段之间没有更改监测设置或同步NVML插入。',
 '![准备与温度](figures/03_preparation_and_temperature.png)','',
 '## 监测频率的有限对照','']
me=d['monitor_effect']
if me:text+=[f"按每层两个进程汇总，20Hz相对1Hz：连续提交A的完整周期变化{pct(me['A_20Hz_over_1Hz_cycle'])}，加间隔B变化{pct(me['B_20Hz_over_1Hz_cycle'])}；B相对A的吞吐比再变化{pct(me['B_advantage_20Hz_over_1Hz'])}。这是小样本描述，不是已分离全部硬件状态的因果效应。"]
text+=['','|块|阶段|模式|CPU-ready均值us|实际ready到下次开始us|SM读数中位MHz|power计数占比|覆盖阶段比例|thermal计数占比|','|---|---:|---|---:|---:|---:|---:|---:|---:|']
for x in d['phases']:
 if x['kind']!='matched' or not x['measured']:continue
 power=x['counters'].get('power_violation');thermal=x['counters'].get('thermal_violation');clock=x['sampled_clock_mhz']
 text.append(f"|{x['block']}|{x['phase']}|{x['mode']}|{x['cpu_ready_us']['mean']:.2f}|{x['ready_to_next_begin_us']['mean']:.2f}|{clock['q50'] if clock else 'NA'}|{100*power['fraction']:.2f}%|{100*power['phase_coverage_fraction']:.2f}%|{100*thermal['fraction']:.3f}%|")
text+=['','计数只在完整落于阶段内的样本之间取差，整卡范围、非单kernel归因。violationTime单位ns、referenceTime单位us。观察频率不等于传感器真实刷新频率；同样读数不等于有效时钟真正固定。',
 '## 已完成与仍未完成','',
 '已完成本轮有界的统一准备流程四进程复验、全部数值验证、原始重建和四张图；输入、代码、二进制、前轮交付完整性都可核查。',
 '未完成：锁频因果对照、硬件缓存/访存计数器、无其他GPU客户端的完整调度隔离、冷热状态全因子矩阵、未见输入和真实应用的自适应策略验证。当前sudo非交互权限仍不可用，未使用历史口令。没有更改时钟/功耗设置或关闭保护。',
 '下一步需要有控制地复现旧慢态，并在相同输入与阶段安排下比较稳定低频和原动态时钟。若没有成功触发旧慢态，单纯增加冷却后重复次数不能关闭它的根因。当前没有证据证明固定180秒空闲、移除C/D、温度或某个单独因素是慢态少见的原因。',
 '本轮不新增NUMA算法，不把运行时间变化当作物理SM/内存拓扑证据。下一步若要继续，应先取得可用的保守锁频对照；再决定是否需要缓存/调度诊断。只有状态可控后空间差异仍可重复且真实负载净收益成立，才支持原NUMA优化命题。',
 '论文角度需要的是可重复的机制、可提前使用的决策和独立负载上的净收益。当前这轮提供的是纠正比较条件与缩小解释范围的证据，不能单凭一个正百分比宣布论文方案成立。',
 '## 预算、失败记录与复算','',
 f"本轮GPU-worker {a['new_gpu_minutes']:.6f}/{a['new_cap_minutes']:.2f}分钟；继承{a['prior_gpu_minutes']:.6f}分钟，累计{a['cumulative_gpu_minutes']:.6f}/330分钟。固定空闲准备单列{a['fixed_idle_cpu_only_s']:.3f}秒。数值检查{a['numerical_records']}条通过。",
 f"成功worker原始请求{d['counts']['requests']:,}条，其中正式测量{d['counts'].get('formal_measured_requests',0):,}条、正式conditioning {d['counts'].get('formal_conditioning_requests',0):,}条。smoke单列，不混入四块比较。",
 f"账本状态：{[(x['key'],x['status']) for x in a['workers']]}。所有失败若存在也保留并计账；没有为增加样本量自动续跑。",
 '解压后执行根目录recompute.py，使用Python+NumPy从raw重建派生结果并核对，不需要CUDA/Torch或原工程目录。源码快照、输入哈希、各字段查询起止、准备阶段遥测和数学二进制都在包内。前轮完整raw不重复，保留其交付哈希与摘要作为上下文。独立解压QA见外部交付索引。']
formatted=[]
for line in text:
 if line and formatted and formatted[-1] and not(line.startswith('|') and formatted[-1].startswith('|')):formatted.append('')
 formatted.append(line)
(ROOT/'reports/T10_MATCHED_PACING_REPORT.md').write_text('\n'.join(formatted)+'\n');print('REPORT_WRITTEN')
