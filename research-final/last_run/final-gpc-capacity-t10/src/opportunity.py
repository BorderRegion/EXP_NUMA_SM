from common import *
import statistics,math
rows=[];capacity=[]
for b in range(2):
 p=RUN/'raw'/('P3_DEV_0_retry2' if b==0 else f'P3_DEV_{b}');rows+=read(p/'PHASES.json');capacity+=read(p/'CAPACITY.json')
text=['# 机会量级：CAP冻结前的开发测量','','本文件仅用两开发过程，先于任何CAP确认。小幅估计不作为删减真实四锚干预的门控。','', '100W/动态受限状态下，下面都是本次服务代理和完整执行成本，不能解释为稳定硬件上限。','', '|锚|scope|N19 ready us|E56 DIRECT us|五组SM us|五组相对单组综合差额 us|并发理想SM尾部|并发理想等份尾部|理想容量尾部|','|---|---|---:|---:|---:|---:|---:|---:|---:|']
for cid,scope in sorted({(r['case'],r['scope']) for r in rows}):
 def gm(action):return math.exp(statistics.mean(math.log(r['ready_us']) for r in rows if r['case']==cid and r['scope']==scope and r['action']==action and r['status']=='MEASURED'))
 rates=[]
 for g in [0,1,2,3,5]:rates.append(math.exp(statistics.mean(math.log(r['capacity']) for r in capacity if r['case']==cid and r['scope']==scope and r['gpc']==g and r['kind']=='CONCURRENT')))
 sm=max(w/56/c for w,c in zip([10,12,12,10,12],rates));eq=max(.2/c for c in rates);ideal=1/sum(rates)
 text.append(f'|{cid}|{scope}|{gm("N19"):.4f}|{gm("E56_DIRECT"):.4f}|{gm("SM_PROP"):.4f}|{gm("SM_PROP")-gm("E56_DIRECT"):.4f}|{sm:.6f}|{eq:.6f}|{ideal:.6f}|')
text+=['','代理假设所有工作可连续切分、组间速率可迁移；真实分配仍受完整worker整数切点约束。孤立和并发两层原值见CAPACITY.json，不能以孤立最大值代替真实makespan。','', '概念账式 estimated gain ≈ f*r − h/T − setup/(H*T)。可触及producer占比f、原生动态均衡已消除多少尾部都未独立分解，不能填成已知上限。h是完整五组组织与单组的实测综合差，不是纯launch费用。','', '五GPC总容量完全相等这一假想下，SM比例最大份额12/56，均分1/5，理想尾部下降6.667%。该数学算例既不是GPU实测上限，也不说明原生按固定SM份额分配。','', '未过状态控制门槛时，主结论是条件不足；无论代理是否乐观，四锚六动作有限对照仍完成。']
(RUN/'reports/OPPORTUNITY_BUDGET.md').write_text('\n'.join(text)+'\n')
