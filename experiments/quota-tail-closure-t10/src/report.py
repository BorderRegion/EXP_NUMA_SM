from common import *
import numpy as np,collections
r=RUN/'reports';r.mkdir(exist_ok=True)
rows=read(RUN/'derived/EXPANDED_LABELS.json');comp=read(RUN/'derived/COMPARISONS.json');extra=read(RUN/'derived/EXTRA_ANALYSIS.json');sel=read(RUN/'freeze/SELECTION.json');prefix=read(RUN/'freeze/PREFIX.json');audit=read(r/'FINAL_AUDIT.json')
def gm(v):return float(np.exp(np.log(v).mean()))
def table(headers,items):return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']+['| '+' | '.join(map(str,x))+' |' for x in items])
def fmt(x):
 if x['structural_alias_all_blocks']:return '同一执行计划（alias）'
 lo,hi=x['ci_change_percent'];return f"{x['time_change_percent']:+.3f}% [{lo:+.3f}, {hi:+.3f}]；{x['faster_blocks']}/{x['blocks']}块快"
def get(cid,label,ref,stage='S3',metric='job_output_ready_us',tag=''):
 return next(x for x in comp if x['stage']==stage and x['case']==cid and x['label']==label and x['reference']==ref and x['metric']==metric and x['tag']==tag)
def absrow(cid,label,stage='S3'):return next(x for x in extra['absolute'] if x['stage']==stage and x['case']==cid and x['label']==label)
parts=[f'''# T10 资源份额、尾部释放与拓扑增量：收束报告

运行 `{RUN.name}`。本机一张T10；采用20261019附件的限定方案。**既定测量与审计已完成；没有证明冻结的拓扑动作池胜过强原生／简单方案，因此按本轮规则暂停这一T10、这对负载、静态共置切入点的自动论文扩展。**

## 直接结论

1. **尾部释放有工程作用，但“胜过差一些的并发”不等于“胜过最强简单执行”。** LONG冻结的普通NEUTRAL 10/46、k=14 RELEASE，相对相同集合的FIXED耗时下降24.972%，相对SHARED56下降10.188%；相对开发期冻结的最佳串行，却增加0.633%，97.5%区间为[−0.504%, +2.105%]，未分辨出净优势。
2. **更大的拓扑候选池没有得到不同的最终主方案。** LONG的JOINT_POOL与Q_ONLY完全相同；RAGGED的Q_ONLY、SIMPLE_SPREAD、JOINT_POOL全部选择SERIAL_GEMM_FIRST。这些是执行计划alias，不是两次独立测试恰好相等。
3. **局部正结果保留。** LONG在固定q=10、RELEASE、k=14后，PACK比NEUTRAL快1.601%，95%探索性区间[−2.529%, −0.902%]，6/6块方向一致。但PACK对冻结最佳串行仅−0.979%，区间[−2.558%, +0.414%]；再加上明显状态波动、有限成员轮换，它还不足以成为已确认的部署净加速。不能在确认集上改选PACK，再回写冻结主张。
4. 背景翻倍后，LONG冻结方案相对冻结最佳串行为−0.871%，95%区间[−2.721%, +0.561%]，仍未分辨；RAGGED仍是串行alias。没有按这个结果重算k或改背景量。

这不是证明所有GPU、配额或调度器都没有价值。它限定了这张卡、这两个算子工作量、五个预定份额、这条静态切点公式和三种布局规则的证据边界。保留现有N19/E56快核与全部有效正负结果，不自动扩展q、shape、mask、时钟或选择器。

## 口径与完成范围

指标为`T_candidate/T_reference`，表中时间变化`100×(r−1)`：**负数快、正数慢**。每phase平均16个完整job，再按进程块配对。5000次整块bootstrap；每个主job的JOINT_POOL对冻结BEST_NATIVE／BEST_SIMPLE使用97.5%边际区间，其余95%探索性。没有对历史全部探索做统一多重校正，也不把16重放、32请求、SM或同一计划的标签当独立硬件样本。''',
table(['阶段','方案标签数','实际独立计时phase','说明'],[['S1',136,136,'2开发块；两个任务分别单跑'],['S2',132,132,'2开发块；33动作×2job'],['S3',120,84,'6确认块；72主比较标签+36位置消融+12模式消融'],['比例留出',48,28,'4新块，背景调用翻倍，规则不变']]),
f'''436个预定标签全部有数据／明确alias，对应380个实际主phase；另有128个短锚点/A-A，共508个有效phase、{audit['timing_rows']}条原始计时。各主phase为两个8-job扫次，第一轮按冻结种子打乱，第二轮逆序；每段同节奏暖身至少2个job且50ms。四槽按全局请求编号连续轮换。所有计划与数值参考先构建，正式段后只对照缓存的参考输出，不在方法之间重建FP64参考。

初始S1块0在汇总写出前发生重复`task`字段异常，尚未产生可用phase文件，内存中的计时未能恢复；错误日志和11.294秒预算仍保留。修复元数据汇总后，以相同预定块重跑，之后才计算k和选择。不能把这次失败称为“原始计时全部保存”。有效正式样本没有按快慢删除。

## 硬件、资源与同体约束

新RM读取及最终复读一致：物理GPC0/1/2/3/4/5为10/12/12/10/0/12SM。可选私有GET仍有权限缺项，未用于猜测屏蔽原因；没有SET、驱动修改、设备重置或保护修改。公开2SM资源合并与实际SM探测核对了12块×15集合的前景／互补背景，共360份资源名单；primary实际资源属性为56SM。完整TPC均保留，无遗漏、重叠或占位CTA。

新轮次直接复用上一轮E56两份二进制及数学源码，哈希一致；原N19保留，S0进行了有限原生回归和数值对照。GQA保持16B加载、W、CTA/block/shared、原DIRECT/BLIND、页表、归并、合法末位更新与复位；LONG为BLIND/W32，RAGGED为DIRECT/W16，二者均为原非融合两核路径。新变化在宿主构造的资源集合和完整请求之间的device依赖，不新增调度kernel、GPU路由表或中间CPU等待。

每job仍为32个变化Q/newKV的固定长度append+Attention；背景1024×2048×4096 FP16输入、FP32计算/输出，alpha=1、beta=0，64MiB workspace。LONG为7次GEMM，RAGGED为9次；留出改为14/18次。FG与BG所有可写/输入区间核对不重叠。不是逐token增长、动态KV生命周期或整模型SLA。

捕获的所有正式GEMM图中均为 `turing_s1688gemm_fp16_256x128_ldg8_stages_32x1_nn`，grid=8×8×2、block=256、shared=16384字节；math mode和调用参数一致。GemmEx接口没有提供可用内部算法ID，记NA。同名同几何不能保证一切执行行为相同，不能由此唯一归因GPC共享总线。

各suite预先创建要用的计划，未选的Green对象空闲存活。因此开发池与更小确认池的上下文环境也不同；这是明确的作用域限制，不把孤立曲线机械预测为真实并发。

## S1：孤立容量与46SM异常

下表单位ms，列出两个开发块的完整工作GPU区间；56端点各自全资源单跑。对于Qq，前景使用q SM，背景使用56−q SM。没有dummy负载，没有用串行第二任务的“从job起点完成时间”当纯服务时间。''']
for cid in ['LONG','RAGGED']:
 items=[]
 for label in ['PRIMARY56','GREEN56']+[f'{fam}_Q{q}' for q in [10,20,28,36,46] for fam in ['NEUTRAL','PACK','SPREAD']]:
  cols=[]
  for task in ['FG','BG']:
   rr=sorted([x for x in rows if x['stage']=='S1' and x['case']==cid and x['task']==task and x['label']==label],key=lambda x:x['block']);cols.append(' / '.join(f"{x['job_gpu_us']/1000:.4f}" for x in rr))
  k=prefix[cid][label]['k'] if label in prefix[cid] else 'NA'
  items.append([label,*cols,k])
 parts+=['### '+cid,table(['资源条件','32次FG：块0/1 ms','全部BG：块0/1 ms','冻结k'],items)]
parts+=['''LONG单独背景：PRIMARY56为6.122/6.688ms，GREEN56为6.100/5.941ms，SPREAD对应GREEN46为6.253/6.762ms；RAGGED对应7.599～8.183ms等量级。**单跑46SM并没有复现上一轮共置时约减半的背景时间。** LONG primary与green全资源也有块间差异，但只有两个开发块，不能据此建立稳定上下文优势。

同体资源量和并发执行历史仍有交互；本轮四份独立活动采集保留了BG_PRIMARY56/BG_GREEN46以及SHARED/RELEASE。没有锁频对照或流量计数，不能把差异唯一解释为功耗、cache、互连或计时bug。单跑曲线不严格按SM数线性缩放；不强行拟合单调模型。

![孤立容量](figures/01_isolated_capacity.png)

## S2：固定池选择与完整开发值

k只来自两个孤立块GPU服务区间的几何平均，`clamp(floor(32×T_bg/T_fg32+0.5),1,31)`；分子分母都是整份工作，不混入单次时间。此指标在联合测量前冻结。S2按完整job主机output-ready选型，两个块几何平均；完全平手按原生、较少准备、固定索引优先。

Q_ONLY池13动作，SIMPLE_SPREAD池13动作，JOINT_POOL池33动作。PC_STAR是开发最佳分区动作，即使原生更快仍做消融；它不等同生产启用。''',
table(['job','Q_ONLY','SIMPLE_SPREAD','JOINT_POOL','PC_STAR','BEST_NATIVE','BEST_SIMPLE'],[[cid]+[sel[cid][k]['label'] for k in ['Q_ONLY','SIMPLE_SPREAD','JOINT_POOL','PC_STAR','BEST_NATIVE','BEST_SIMPLE']] for cid in ['LONG','RAGGED']])]
for cid in ['LONG','RAGGED']:
 parts+=['### '+cid+'：全部33动作',table(['动作','k（FIXED不使用）','块0 ms','块1 ms','几何平均ms'],[[x['label'],x['action']['k'],*[f'{v/1000:.4f}' for v in x['development_values']],f"{x['geomean_output_ready_us']/1000:.4f}"] for x in sel[cid]['all_development_actions']])]
mode_best=[]
for cid in ['LONG','RAGGED']:
 for mode in ['FIXED','RELEASE']:
  best=min([x for x in sel[cid]['all_development_actions'] if x['action']['mode']==mode],key=lambda x:x['geomean_output_ready_us'])
  mode_best.append([cid,mode,best['label'],f"{best['geomean_output_ready_us']/1000:.4f}",f"{100*(best['geomean_output_ready_us']/sel[cid]['BEST_NATIVE']['geomean_output_ready_us']-1):+.3f}%"])
parts += [table(['job','模式','本开发池该模式最低动作','完整job ms','相对开发最佳原生'],mode_best),'这里只是在预定有限池内的开发排名，不是已知全局最佳份额。孤立GQA增加份额通常更快，低SM背景代价增大；但联合曲线不能由这些孤立值简单相加或取max预测。']
parts+=['![开发矩阵](figures/02_development_matrix.png)','''## S3：冻结计划的新块确认

下面均为六个新进程。绝对时间取块均值的几何平均，单位ms；前后台完成时间从同一job起点计，所以串行第二方包含等待第一方。比例不是单请求p99。''']
for cid in ['LONG','RAGGED']:
 parts+=['### '+cid,table(['策略','整项就绪ms','前景完成ms','背景完成ms'],[[label]+[f"{absrow(cid,label)['geomean_ms'][k]:.4f}" for k in ['job_output_ready_us','foreground_completion_us','background_completion_us']] for label in ['SERIAL_GQA_FIRST','SERIAL_GEMM_FIRST','SHARED56','Q_ONLY','SIMPLE_SPREAD','JOINT_POOL']]),table(['JOINT_POOL参照','整项时间变化','前景完成变化','背景完成变化'],[[ref]+[fmt(get(cid,'JOINT_POOL',ref,metric=k)) for k in ['job_output_ready_us','foreground_completion_us','background_completion_us']] for ref in ['SERIAL_GQA_FIRST','SERIAL_GEMM_FIRST','SHARED56']]),table(['冻结主检验','97.5%边际区间'],[[x['tag']+' → '+x['reference'],fmt(x)] for x in comp if x['stage']=='S3' and x['case']==cid and x['metric']=='job_output_ready_us' and x['tag'] in ['FROZEN_BEST_NATIVE','FROZEN_BEST_SIMPLE']])]
parts+=['''## 同份额位置消融与尾部释放

LONG固定q10、RELEASE、k14；RAGGED固定q28、RELEASE、k28。NEUTRAL/PACK/SPREAD共用该job的同一个k。相反模式只在PC_STAR同一SM集合执行，FIXED运行完整32请求，RELEASE总请求数仍32。''',table(['job','比较','完整job变化95%'],[[x['case'],x['label']+'/'+x['reference'],fmt(x)] for x in comp if x['stage']=='S3' and x['metric']=='job_output_ready_us' and x['tag'] in ['SAME_QUOTA_MODE_K','RELEASE_VS_FIXED']]),'''LONG PACK的局部正效应没有被删去；但它不是开发冻结的JOINT方案。对最佳串行的描述性比较为−0.979%且区间跨零；RAGGED PACK对同一个串行反而慢6.673% [5.082%, 8.110%]。更大的池并没有在独立确认上带来额外净收益。完整消融对三种原生的前后台、总时长也在COMPARISONS.json，带`DESCRIPTIVE_ABLATION_VS_NATIVE_NOT_SELECTED`标签，不能当成新选择结果。

![冻结确认与消融](figures/03_confirmation_and_ablation.png)

## 为什么静态k没有消除长尾

RELEASE以device事件依赖等待前缀和全部背景都结束，再在已准备好的PRIMARY56上执行剩余请求。没有迁移活跃kernel，也没有在线扩容Green对象。正式前缀完成事件仅用于依赖、禁用计时；下面前缀/后缀时间来自独立诊断，不能替代正式主结果。''']
ts=[x for x in read(RUN/'raw/S4_diagnostics/TIMESTAMPS_AND_CHECKS.json') if x['kind']=='INDEPENDENT_RELEASE_TIMESTAMPS']
parts += [table(['job','q/k','背景完成ms','前缀完成ms','后缀开始ms','后缀跨度ms'],[[x['case'],f"{x['action']['q']}/{x['action']['k']}"]+[f'{v:.4f}' for v in (np.mean(x['rows'],axis=0)/1000)[[2,4,6,5]]] for x in ts]),'''LONG的背景大约4ms完成，k14前缀却到约10ms才完成；这不是“背景完成就立即释放”，而是预定合法请求边界的双依赖。按单跑速度预测的前缀/背景平衡，在并发时失配。RAGGED的k28只给全资源后缀留下4个请求，RELEASE/FIXED差异较小且区间跨零。此处说明服务时间代理有偏差；没有事后扫描k来补正结果。

代表RELEASE的CUPTI中，前缀与背景确有重叠，后缀与背景重叠为0；128个GQA kernel节点与14个GEMM节点对应两份完整job。S0切点1/6/31检查及实际32请求图覆盖、KV边界检查通过。正式计时依赖代价全部计入，不使用诊断时间线证明正式速度。

![独立阶段时间线](figures/04_release_stage_diagnostic.png)

## 背景倍增留出

四个新块，LONG背景14次、RAGGED18次。q、家族、模式、k、选择和冻结强参照一律不变。''']
for cid in ['LONG','RAGGED']:
 parts += ['### '+cid,table(['策略','整项就绪ms','前景完成ms','背景完成ms'],[[label]+[f"{absrow(cid,label,'HOLDOUT')['geomean_ms'][k]:.4f}" for k in ['job_output_ready_us','foreground_completion_us','background_completion_us']] for label in ['SERIAL_GQA_FIRST','SERIAL_GEMM_FIRST','SHARED56','Q_ONLY','SIMPLE_SPREAD','JOINT_POOL']]),table(['JOINT_POOL参照','完整job变化95%'],[[ref,fmt(get(cid,'JOINT_POOL',ref,stage='HOLDOUT'))] for ref in ['SERIAL_GQA_FIRST','SERIAL_GEMM_FIRST','SHARED56']])]
parts+=['''## 状态波动与敏感性

不删异常/慢值，不做时钟回归。短锚点各4job，主phase16job，不能将锚点的波动程度直接当作每个配对比较的误差条，但必须揭示它。LONG确认首个A/A平均变化−12.973%，尾部A/A为+4.730%；某些状态变化显著大于1%级位置差异。''',table(['阶段','job','锚点比值','变化95%'],[[x['stage'],x['case'],x['contrast'],fmt(x)] for x in read(RUN/'derived/ANCHORS.json')]),table(['job','比较','第一扫次变化','逆序扫次变化'],[[cid,con]+[f"{next(x['time_change_percent'] for x in extra['sweep_sensitivity'] if x['case']==cid and x['comparison']==con and x['sweep']==s):+.3f}%" for s in [0,1]] for cid in ['LONG','RAGGED'] for con in ['JOINT_POOL/'+sel[cid]['BEST_NATIVE']['label'],'ABLATE_PACK/ABLATE_NEUTRAL','ABLATE_SPREAD/ABLATE_NEUTRAL']]),'''两扫次都保留。LONG主方案对最佳串行由第一扫次−0.328%变为逆序扫次+1.598%；PACK/NEUTRAL分别为−0.645%、−2.552%。这削弱了对细小效应的稳健性和唯一因果解释，不能因为六块bootstrap区间很窄而忽略顺序/状态偏差。没有据此再开状态搜索。

## 资源暴露限制

本轮不是上一轮五PACK/五SPREAD严格同50SM等频设计。下表为六个确认块中，各份额和家族的前景SM暴露次数合计；每个块的实际SM/TPC名单在freeze/resource_sets.json。GPC编号不是空间坐标，有限轮换不能唯一隔离物理距离或共享总线。''']
exposure=[]
for q in [10,20,28,36,46]:
 for fam in ['NEUTRAL','PACK','SPREAD']:
  p=[x for x in read(RUN/'freeze/resource_sets.json')['plans'] if x['block'] in range(2,8) and x['foreground_sms']==q and x['family']==fam];counts={str(g):sum(x['foreground_gpc_counts'][str(g)] for x in p) for g in [0,1,2,3,5]};exposure.append(dict(q=q,family=fam,confirmation_GPC_SM_exposures=counts))
write(RUN/'derived/GPC_EXPOSURE.json',exposure)
parts+=[table(['q','家族','GPC0','GPC1','GPC2','GPC3','GPC5'],[[x['q'],x['family']]+[x['confirmation_GPC_SM_exposures'][str(g)] for g in [0,1,2,3,5]] for x in exposure]),'''## 准备、选型与回本

最初S4成本的首个原生动作承担首次E56内核加载，形成不一致模块状态；原记录保留。正式成本代数使用独立`S4_costs_warm_control`：两种primary数学路径统一预热后，逐方案新建资源/Graph对象，计公共资源枚举及完整计划构造。输入与参考准备单列排除；代码已驻留，因此不是进程冷启动。构造包含研究所需位置核对及capture前置执行，也不是生产最低成本。不能将一次测得的准备差额当精确部署模型。

H=1/100/1000列为 **实测准备 + H×确认期稳态均值的代数估计**，没有真实运行这些H，也不含以前的选型费用。''',table(['job','策略','准备ms','稳态job ms','H1估计ms','H100估计ms','H1000估计ms'],[[x['case'],x['label'],f"{x['setup_ms']:.3f}",f"{x['steady_ms']:.4f}"]+[f"{x['estimate_total_ms'][str(h)]:.3f}" for h in [1,100,1000]] for x in extra['cost_estimates']]),table(['job','JOINT参照','稳态节省ms/job','额外准备ms','有支持的代数回本job数'],[[x['case'],x['reference'],f"{x['steady_saving_ms']:+.4f}",f"{x['additional_setup_ms']:+.3f}",x['arithmetic_break_even_jobs'] if x['arithmetic_break_even_jobs'] is not None else 'NA：无分辨出的正节省或alias'] for x in extra['payback']]),f'''两job完整有效开发worker耗时{extra['selection_cost']['valid_development_worker_seconds']:.3f}秒，另有初始失败11.294秒。包含所有候选构造、资格和采样，是共享研究选型成本，不冒充单个生产计划最低费用；13/13/33候选池的规模差必须披露。CPU冻结规则计算未独立计时，记NA。只比较稳态或H代数不能声称选型免费。

对更强串行没有稳定正节省，就没有得到有限回本点；不能靠无限H救成净加速。相对SHARED的回本只针对这个较弱参考，不解决原生串行已相当或更好的问题。

## 验证、预算和剩余缺口

共{audit['numerical_check_records']}条正式/资格数值检查记录通过。DIRECT沿用原raw-bit资格，LONG BLIND沿用原容差与非确定性说明；没有放宽数学合同。新旧E56源码与二进制哈希一致。4次CUPTI活动采集；有限memcheck/synccheck均0错误，覆盖LONG/RAGGED在k1/k31的完整释放任务，不声称每次正式请求都做过sanitizer。

GPU-worker {audit['worker_seconds']/60:.3f}/90分钟，计入失败与所有诊断；加上一轮账本为{audit['combined_seconds']/60:.3f}/180分钟，未清零历史。保守墙时从06:40 UTC开始，硬截止10:40 UTC；无须花满额度。100W、82°C worker保护与原有风扇/过温策略保持；未锁频、未停止桌面或其他GPU客户端。新下载/安装/SSH/付费/驱动/屏蔽修改为0。

缺口包括：内存/互连硬件流量、内部cuBLAS算法ID、精确物理home、跨日/跨卡复验、专用decode强后端、真实在线动态KV生命周期。部分阶段计时只在独立诊断提供。这里既不能宣布物理NUMA，也不能证明严格无差异。

本轮最实在的工程结果是可复查的合法尾部释放路径及其边界：普通阶段安排能修复固定10/46的一部分长尾，但冻结方案尚未胜过最强简单参考。局部PACK正结果、弱/负留出结果和实现错误全部记录。按预设收束条件，暂停自动扩大这一论文切入点，保留可用快核及证据。

## 文件与CPU复算

- `derived/MEASURED_PHASES.json`：508个实际phase。
- `derived/EXPANDED_LABELS.json`：436个标签与alias来源，不能当436次独立计时。
- `derived/COMPARISONS.json`：全部主比较、前后台、消融与明确标记的描述性对照。
- `derived/EXTRA_ANALYSIS.json`：六块绝对时间、扫次/锚点敏感性、GEMM图、成本代数。
- `freeze/PREFIX.json`、`freeze/SELECTION.json`：切点和选型及完整开发源值。
- `raw/`：全部有效请求、资源/图/数值/遥测，以及失败日志。原失败内存计时未写出，这个缺口如实保留。
- `reports/FINAL_AUDIT.json`、`ENGINEERING_NOTES.json`：审计及工程修复。

`recompute.py`只做CPU复算与哈希核对，不启动GPU，不执行附件中的历史命令。''']
(r/'T10_QUOTA_TAIL_CLOSURE_REPORT.md').write_text('\n\n'.join(parts)+'\n')
print('REPORT_WRITTEN')
