from common import *
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib.font_manager import FontProperties
A=REPO/'T10_RESEARCH_FINAL';out=A/'sources/figures';out.mkdir(exist_ok=True)
font=FontProperties(fname='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',size=9)
groups=[('应用与算子基础',[(1,'3DGS / CSR','未胜原生'),(2,'强基线补测','局部匹配未变净收益'),(3,'算子内调度方案','候选未实现'),(4,'接入与100W','功耗控制并非锁频'),(5,'CUTLASS与融合','同体正数，仍输库'),(6,'同q复核','普通开销改善')]),('地址与位置规律',[(7,'逐SM地址探针','小集合局部结构'),(8,'冻结0x33规则','低并发约1%，有限'),(9,'真实PC handoff','退化为简单同组')]),('测量与选择器',[(10,'选择性重排','冻结计划回退LIB'),(11,'修复与A/A','状态仍不稳定'),(12,'瞬态与F4','反复跳变并非开头'),(13,'提交节奏','主+20.7%，复验负'),(14,'统一准备复验','等待成本未回本')]),('真实快核接入',[(15,'SM通信与地址','有条件的原型正数'),(16,'真实GEMM归并','未胜原CUTLASS'),(17,'页队列与强配方','普通GEMM配方有效'),(18,'GQA复用与融合','普通kernel明显改善'),(19,'16B向量搬运','保留GQA工程快核')]),('拓扑与严格对照',[(20,'Softmax配对','热输入条件正数'),(21,'工作/归并者控制','严格主条件未通过'),(22,'实读GPC屏蔽','确认非均匀配置'),(23,'TPC/GPC分层','未胜强简单对照'),(24,'通信尾部代理','固定BASE54较强'),(25,'真实核低成本采样','校准后无新增收益')]),('最后三轮收束',[(26,'GPC竞争与共置','局部现象，未越基线'),(27,'份额与尾部释放','释放有效，未胜串行'),(28,'状态与容量CAP','状态未达标；CAP输N19')])]
fig,ax=plt.subplots(figsize=(18,9));ax.set_xlim(0,6);ax.set_ylim(0,7.5);ax.axis('off')
for col,(title,items) in enumerate(groups):
 ax.text(col+.5,7.05,title,ha='center',fontproperties=font,fontsize=13,weight='bold')
 if col<5:ax.annotate('',xy=(col+1.04,6.65),xytext=(col+.96,6.65),arrowprops=dict(arrowstyle='->',color='#777'))
 for j,(n,title,outcome) in enumerate(items):
  y=6.25-j*.94;color='#e2f1e8' if n in [17,18,19,22] else '#fff0d7' if n in [7,8,15,20,24,28] else '#e9eef4'
  box=FancyBboxPatch((col+.07,y-.36),.86,.75,boxstyle='round,pad=0.02',linewidth=.7,edgecolor='#91a0ad',facecolor=color);ax.add_patch(box)
  ax.text(col+.5,y+.12,f'{n:02d}  {title}',ha='center',va='center',fontproperties=font,fontsize=10)
  ax.text(col+.5,y-.15,outcome,ha='center',va='center',fontproperties=font,fontsize=8.8)
  if j<len(items)-1:ax.annotate('',xy=(col+.5,y-.55),xytext=(col+.5,y-.40),arrowprops=dict(arrowstyle='->',color='#777',lw=.8))
ax.text(3,.2,'保留工程资产与单设备表征；未证明拓扑／地址亲和超过强基线的稳定净加速。阶段数不是独立样本数。',ha='center',fontproperties=font,fontsize=12)
fig.suptitle('T10：28个阶段的探索与收束（2026-10-14 至 10-21）',fontproperties=font,fontsize=18);fig.tight_layout(rect=(0,0,1,.95));fig.savefig(out/'exploration_28.png',dpi=160);fig.savefig(out/'exploration_28.pdf');fig.savefig(out/'exploration_28.svg');print('EXPLORATION_FIGURE_WRITTEN')
