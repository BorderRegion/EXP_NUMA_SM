"""A short reader entry after the complete audited campaign."""
import json
from common import *
r=runroot()
def load(n):return json.loads((r/'derived'/f'{n}.json').read_text())
a=load('COMPLETION_AUDIT');assert a['status']=='COMPLETE_WITH_EXPLICIT_NA';m=load('MICRO_ANALYSIS');f=load('FINE_SUMMARY');runtime=load('RUNTIME_SUMMARY')
fine=next(x for x in f['conditions'] if x['bytes']==2<<20 and x['control_scope']=='BALANCED56SM' and x['cache']==0 and x['cg']==1 and x['mode']==0)
primary=[x for x in m['comparisons'] if x['method']=='M' and x['baseline'] in ['N','T'] and x['metric']=='total_ready_ms']
wins={b:sum(x['ratio']['ci95'][1]<1 for x in primary if x['baseline']==b) for b in ['N','T']}
losses={b:sum(x['ratio']['ci95'][0]>1 for x in primary if x['baseline']==b) for b in ['N','T']}
L=['# 这轮 T10 实验，直白地说','',
f"本轮选定的可执行实验已结束，共用了 {runtime['worker_hours']:.2f} 个 GPU-worker 小时。三族原生负载、位置探测、八策略合成对照和真实释放/重申请/扩容都留下了数据；没有把缺少前提的应用优化格假装跑完。",'',
f"**联合方法尚未显示稳定的完整请求收益。** 九个主条件中，M 相比普通 N 有 {wins['N']} 项的探索性区间完全支持更快、{losses['N']} 项支持更慢；相比简单 T 分别为 {wins['T']} 和 {losses['T']} 项。其余条件的区间跨过零变化，不能写成完全等效。",'',
f"**确实看见了一点可重复的访问偏好。** 2 MiB 小集合中，不同 SM 组访问不同区域的局部差异约 {fine['late_effect']['mean']*100:.2f}%，前后轮相关约 {fine['map_stability']['mean']:.3f}。32 MiB 下不稳定。这还不是物理 NUMA 地图，也不是 SM 间通信延迟测量。",'',
'**有偏好，不等于利用它就更快。** 我们真正执行了八种方案，并把完整请求时间、额外 kernel、布局和重新标定成本都拿出来比较。M 是联合布局与分配；T 用同样信息，只分配任务、不搬数据。下表负数表示 M 更快，正数表示 M 更慢；括号是探索性区间，不能只挑最好的一行。','',
'| 数据/状态 | M 相对普通 N 的时间变化 | M 相对简单 T 的时间变化 |','|---|---:|---:|']
for size in [2<<20,8<<20,32<<20]:
 for mode in range(3):
  cells=[]
  for base in ['N','T']:
   q=next(x for x in m['comparisons'] if x['bytes']==size and x['mode']==mode and x['method']=='M' and x['baseline']==base and x['metric']=='total_ready_ms')['ratio'];cells.append(f"{(q['estimate']-1)*100:+.2f}% [{(q['ci95'][0]-1)*100:+.2f}, {(q['ci95'][1]-1)*100:+.2f}]")
  L.append(f"| {size>>20} MiB / {['热的一遍读取','扫描缓存后的一遍读取','热的四遍复用'][mode]} | {' | '.join(cells)} |")
L += ['', '每格来自 8 个独立进程/分配块，区间为每项 97.5%；这是合成消费者，N 也是相同数学体的普通实现，不是生产库。T/M 在这个均匀归约中的物理访问集合相同，不能仅凭一项微小差异宣称新算法贡献。紧密批量循环中有少数小幅改善，也有退化；它们没有变成表中稳定的完整请求收益，完整结果仍保留。','']
cal=[]
for size in [2<<20,8<<20,32<<20]:
 z=[float(x['calibration']['calibration_total_ms']) for x in m['costs'] if x['stage']=='FORMAL' and x['bytes']==size]
 cal.append(f"{size>>20} MiB 约 {sum(z)/len(z)/1000:.2f} 秒")
L += ['**初始化也有实际代价。** 本实现每次分配的标定平均为 '+ '，'.join(cal)+'。它不是未来最佳实现的理论下限，但必须记入这次实现的账；重新分配或扩容后也重新标定。每种状态的稳态节省、准备开销和描述性回本数见完整报告。','',
'**现在还不能说渲染、稀疏或推理获得了 NUMA 加速。** 本轮测了真实 3DGS 动态帧、真实图结构的 CSR，以及合成 GEMM/attention。应用自己的活跃内存分配尚未验证出可部署的短规则，因此应用 NUMA 候选记为未执行；原生结果不能用来证明“这种负载不适合 NUMA”。已有普通 Q1 对照落后于库的负例也完整保留。','',
'**论文当前能用的是可复验现象、机制对照与适用边界。** 还不能写成“发现了物理 NUMA”“远端流量下降”或“真实应用端到端提速”。没有硬件流量计数，没有第二功耗条件，没有真实 LLM token 部署结果。初始化和布局成本也不能从图里藏掉。','',
'设置保持 100 W 上限，保护服务未改；实际功耗和频率会波动，日志保留。失败过的资格诊断、修正、相机重叠和全部未执行项也都写明。','',
'继续审阅：NUMA_FIRST_V3_T10_REPORT.md → 审阅问题.md → BOTTLENECK_CARDS.md。网页审阅包的复算入口是 review_recompute.py；大原始记录和模型留在本地并附 SHA-256 索引。','']
(ROOT/'直白结论.md').write_text('\n'.join(L).rstrip()+'\n');print('plain-language summary written')
