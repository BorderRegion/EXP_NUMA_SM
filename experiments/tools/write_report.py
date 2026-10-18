#!/usr/bin/env python3
"""Generate the final Chinese evidence report from fixed post-run statistics."""
import pathlib,json,csv,statistics,hashlib,collections,math
ROOT=pathlib.Path(__file__).resolve().parents[1];D=ROOT/'derived/t10';P=ROOT/'reports';P.mkdir(exist_ok=True)
def load(name):return json.loads((D/name).read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def table(headers,rows):return '\n'.join(['| '+' | '.join(map(str,headers))+' |','|'+'|'.join(['---']*len(headers))+'|']+['| '+' | '.join(map(str,r))+' |'for r in rows])
def ci(v,level='ratio_ci95'):return f"{v['ratio']:.4f} [{v[level][0]:.4f}, {v[level][1]:.4f}]"
def main():
 stats=load('application_statistics.json');mech=load('mechanism_statistics.json');audit=load('audit.json');completion=load('completion.json');cost=load('costs.json');assert audit['status']=='PASS'
 sessions=list(csv.DictReader(open(D/'session_summaries.csv')));costrows=list(csv.DictReader(open(D/'execution_costs.csv')));runs=[json.loads(x)for x in (ROOT/'run_index.jsonl').read_text().splitlines()]
 names=[('W1','bonsai'),('W1','train'),('W2','ca-GrQc'),('W2','web-Google')];results=[];costtable=[];lifecycle=[]
 for w,name in names:
  means=[statistics.mean(float(r['mean_ms'])for r in sessions if r['input']==name and r['policy']==pol)for pol in 'NRM']
  results.append([w+'/'+name,*[f'{v:.6f}'for v in means],ci(stats[w+'/'+name+'_M/N']),ci(stats[w+'/'+name+'_M/R'])])
  delta=means[2]-means[0];lifecycle.append([name,*[f'C + {n*delta:.4f} ms'for n in [1,100,1000,10000]]])
  a=[r for r in costrows if r['input']==name and r['policy']=='M'];costtable.append([name,f"{statistics.mean(float(r['plan_load_upload_ms'])for r in a):.4f}",a[0]['plan_bytes'],f"{statistics.mean(float(r['dispatch_cpu_ms'])for r in a):.3f}"if a[0]['dispatch_cpu_ms']else'未单列',f"{statistics.mean(float(r['memory_used_bytes'])for r in a)/(1024**2):.1f}"if a[0]['memory_used_bytes']else'未记录峰值'])
 cap=list(csv.DictReader(open(D/'capacity.csv')));capacity=[]
 for size in range(3):
  for f in range(4):
   a=[r for r in cap if int(r['family'])==f and int(r['size'])==size and r['mode']=='concurrent'];rs=[]
   for b in range(3):
    x=sorted([r for r in a if int(r['process_block'])==b],key=lambda r:int(r['group']));rs.append((float(x[1]['tasks_per_ms'])/int(x[1]['sms']))/(float(x[0]['tasks_per_ms'])/int(x[0]['sms'])))
   iso=[r for r in cap if int(r['family'])==f and int(r['size'])==size and r['mode']=='isolated'];transfer=[]
   for g in [0,1]:transfer.append(statistics.mean(float(r['tasks_per_ms'])for r in a if int(r['group'])==g)/statistics.mean(float(r['tasks_per_ms'])for r in iso if int(r['group'])==g))
   capacity.append([f'K{f}', ['small G1','nominal G2','large G3'][size],f'{statistics.mean(rs):.4f} ± {statistics.stdev(rs):.4f}',*[f'{x:.3f}'for x in transfer]])
 model=list(csv.DictReader(open(D/'prediction_error.csv')));modelrows=[]
 for pol in 'RM':
  a=[float(r['relative_error'])for r in model if r['policy']==pol];modelrows.append([pol,len(a),f'{100*statistics.median(a):.2f}%',f'{100*statistics.median(abs(x)for x in a):.2f}%'])
 e3rows=[[f'd{d}/l{l}',ci(mech[f'd{d}/l{l}_M/N']),ci(mech[f'd{d}/l{l}_M/R'])]for d in range(3)for l in range(2)]
 counts=table(['阶段','成功进程','失败进程'],[[s,sum(r['stage']==s and r['status']=='SUCCESS'for r in runs),sum(r['stage']==s and r['status']=='FAILED'for r in runs)]for s in sorted({r['stage']for r in runs})])
 buildids=sorted({r['build_id']for r in runs if r['stage']in['E2','E3','E4_W1','E4_W2']});builds={b:json.loads((ROOT/'build'/b/'build.json').read_text())for b in buildids}
 sources={str(p.relative_to(ROOT)):sha(p)for p in sorted((ROOT/'src').glob('*'))if p.is_file()};sources['GPU_COMPUTE_TOPOLOGY_DUAL_20261014/tools/reference.py']=sha(ROOT/'GPU_COMPUTE_TOPOLOGY_DUAL_20261014/tools/reference.py')
 source_hash=hashlib.sha256(json.dumps(sources,sort_keys=True).encode()).hexdigest()
 inputs={name:json.loads((ROOT/'assets/prepared'/name/'manifest.json').read_text())for _,name in names};inputs['model_downloads']=[json.loads(x)for x in (ROOT/'assets/model_downloads.jsonl').read_text().splitlines()];inputs['sparse_downloads']=[json.loads(x)for x in (ROOT/'assets/sparse/downloads.jsonl').read_text().splitlines()]
 (P/'inputs_manifest.json').write_text(json.dumps(inputs,indent=2));(P/'method_sources.json').write_text(json.dumps(sources,indent=2));inputhash=sha(P/'inputs_manifest.json')
 outcome='TOPOLOGY_OBSERVED_NO_DEPLOYABLE_GAIN'
 summary=dict(platform='t10',device_id_alias='local_t10_01',device_identity=json.loads((ROOT/'environment/device_query.json').read_text()),protocol_hash=sha(ROOT/'GPU_COMPUTE_TOPOLOGY_DUAL_20261014/campaign.json'),local_protocol_hash=sha(ROOT/'preregistration/LOCAL_PROTOCOL.md'),method_source_hash=source_hash,inputs_manifest_hash=inputhash,build_recipe={b:dict(manifest='build/'+b+'/build.json',compilation_ms=m.get('compilation_ms'),source_snapshot='build/'+b+'/source_snapshot')for b,m in builds.items()},available_paths=['Native','Green_G0_56','Green_G1_28_28','Green_G2_18_38','Green_G3_28_28','E2_four_kernel_families','E3_NISLRMP','W1_full_dynamic_3DGS_720p','W2_real_input_CSR_operator'],missing_cells=[dict(cell='RTX5070Ti',status='NOT_RUN_HERE'),dict(cell='T10_cluster_DSM',status='UNSUPPORTED'),dict(cell='physical_GPC_map_and_T',status='NA'),dict(cell='W1_gsplat_production_Bext',status='BASELINE_GAP'),dict(cell='W2_existing_full_production_application',status='SCOPE_GAP'),dict(cell='E5_Truck_resolution_colocation_lifecycle_constants_logging_ablation',status='NOT_TRIGGERED'),dict(cell='Native_trailing_timed_anchor',status='NOT_RUN'),dict(cell='original_CPU_planning_time',status='NOT_INSTRUMENTED')],primary_comparisons=[dict(comparison=k,**stats[k],raw_pairs='derived/t10/paired_M_'+k[-1]+'.json')for k in ['W1_M/N','W1_M/R','W2_M/N','W2_M/R']],scope=dict(n_device=1,independent_unit='process block (E3 uses paired fresh-process batch)',process_blocks_per_cell=6,formal_process_blocks=48,formal_sessions=144,measured_frames_or_requests=73728,cluster_claim=False,gpc_causality=False,cross_device_pooling=False,interpretation='Within-device exploratory; outcome refers to public resource-set observations, not reconstructed physical topology'),outcome=outcome,worker_seconds=cost['worker_seconds'],actual_cost=0,cost_unit='CNY',cost_basis=cost['basis'])
 (P/'platform_summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False))
 import sys;sys.path.insert(0,str(ROOT/'GPU_COMPUTE_TOPOLOGY_DUAL_20261014/tools'));from merge_platforms import merge
 combined=merge([summary]);(P/'combined_review.json').write_text(json.dumps(combined,indent=2,ensure_ascii=False))
 report=f'''# T10 双卡计算拓扑实验平台报告

2026-10-14；单机实际执行；`n_device=1`。本轮 GPU 实验已结束，原始成功与失败记录均保留。

终态：**{outcome}**。这里的“拓扑观测”仅指公开资源分区与实际 SM 覆盖；没有重建物理 GPC 图，也没有证明 floorsweeping 的因果效应。完成了可支持的 E0–E4 有界确认和 E6 交付；E5 未触发。结论不是“所有 GPU 不存在异质性”，而是本卡、本方法、本输入范围尚无超过 Native 与同信息强基线的可部署增量。

1. **两张卡的真实资源是什么？** 本机 CUDA 查询为 Tesla T10、cc 7.5、56 SM、4 MiB L2、15,636,037,632 字节可见全局显存；驱动 580.178.04，API 13.0，编译/运行时 12.0，Green 头文件 12.8。RTX 5070 Ti 未在本机运行，其 70 SM、6 GPC 等仅为任务包的规格背景，不能填作实测。
2. **5070 Ti 的不均衡与 T10 的可比部分？** 本轮无法回答 5070 Ti 实测问题。T10 的普通 CTA、公开 Green 分区、四类有效容量及 N/R/M 方法可组成公共子集；cluster 属性为 0，所有 cluster/DSM 项为 NA，不模拟、不推定永久调度缺口。
3. **原生调度是否已处理不均衡？** 没有足够物理证据断言其机制，但实际端到端 Native 是更强参考：W1 合并 M/N={ci(stats['W1_M/N'])}，W2={ci(stats['W2_M/N'])}。这些结果不支持用静态分组替代 Native 来恢复所谓裁剪损失。
4. **同 SM 数、同逻辑任务的组差异多大？** 28+28 大规模条件的每 SM 并发容量比接近 1；短任务会出现数个百分点到约两成差异，且随类型与并发改变。它包含提交顺序、缓存、DVFS 等影响，不可当作物理单元快慢排名。完整数值见图 3 及容量表。
5. **M 是否胜过 Native 与 R？** 未形成可重复的双重优势。W1 M/R={ci(stats['W1_M/R'])}，W2 M/R={ci(stats['W2_M/R'])}；没有可支持的总体新方法增量。
6. **仅胜人工等分算什么？** 属于机制或工程现象。E3 的 d1/l1 中 M/N={ci(mech['d1/l1_M/N'])}，但 M/R={ci(mech['d1/l1_M/R'])}，不能据此宣称新的部署收益。
7. **类型与并发是否改变容量？** 会，尤其 K3 带宽工作在并发时服务率降低；同一资源集合的并发/隔离比变化明显。类别模型也有迁移误差，不能把单次隔离速率直接当作所有应用的能力常数。
8. **稳态、启动与生命周期成本？** 73,728 条测量记录的在线规划、计划传输和重编译字段均为 0，源码复核一致；组 launch、同步、表访问及相机/请求提交计入主时间。M 计划加载/上传均值约 0.12–0.27 ms。最初 CPU 计划生成、单独 context setup 未计时，生命周期/E5 未运行，因此不提供虚构的精确回本帧数。
9. **两个场景还是两个程序？** W1 是完整动态 3DGS 渲染的 Bonsai/Train 两场景；W2 是另一份真实输入 CSR SpMV 独立算子程序，使用两个 SNAP 图和 cuSPARSE Native。W2 的映射适配器是本轮新写的，未达到“既有生产端到端应用”的更强证据层级。
10. **新增算法能力是什么？** 实现了一个三类有效服务率的初始化静态 minimax 表计划，以及同信息单速率 R；minimax、静态映射、持久 CTA 均为已知方法。当前数据尚不能支持具体的算法创新贡献。
11. **弱正效应、可靠结果与样本不足分别是什么？** Train 的 M/R 约 0.5% 改善被保留，Bonsai 则约 1% 退化；两者相对 Native 均更慢。web-Google 的 M/N 区间跨 1 且较宽，结论不确定。每格只有 6 个进程块，全部区间是本器件探索性估计，不能以帧数增大独立样本量。
12. **值得写完整论文吗？** 不建议把本轮写成“拓扑感知调度带来通用加速”的正结果论文。可以交付严谨的可复现测量/负结果材料。继续投入应先有明确方法差异，再补既有第二应用、第二器件与独立 5070 Ti 数据；不宜在相同方案上继续找有利场景。

## 实测资源与控制边界

公开 API 返回 G0=56，G1=28+28，G2=18+38，G3=28+28；每种布局均包含全部余数，无闲置余数组。三个新进程都观测到完整分配集合。G3 使用公开忽略 co-scheduling 的 split flag，实际集合与 G1 相同，不能视为独立物理布局干预。SM ID 只是逻辑位置标签，未假定其跨设备意义。

E1 运行 Native/G0/G1/G2/G3 各 3 个新进程，128 线程 block 的有限覆盖诊断。它是原上限矩阵的子集，未穷举全部形状和工作量；完整覆盖只说明本次有限任务观测到了所有分配 SM。没有执行 cluster launch，不以 k=1 的普通 launch 冒充 cluster 资格。

![公开资源与逻辑SM集合](figures/01_resource_map.png)

图 1：深蓝为组 0，青色为组 1。图中没有物理 GPC 标签；规格与实测的边界由本节说明。

![能力与未支持项](figures/02_capabilities.png)

环境未锁频，未修改功耗限额或驱动。所有 run 前后健康快照温度范围 {audit['health_ranges']['temperature_c']} °C，SM 时钟范围 {audit['health_ranges']['sm_mhz']} MHz，包含空闲快照；不是逐 kernel 时钟轨迹。任务中未出现记录到的设备丢失、不可纠正 ECC 或启动失败。进程前后 NVML 显存回到 2 MiB，不能用该值代表运行峰值。W1 有帧内显存记录，W2 缺峰值日志。

## 数值合同与真实输入

W1 固定 Graphdeco rasterizer commit `59f5f77e3ddbac3ed9db93ec2cfe99ed6c5d121d`。使用原作者 iteration 30000 模型和相机，每帧真实执行 preprocess、binning、sort 和 render；只扩展 render 的 tile 映射外层，保留原 Native 数值 body。模型激活在共同的 CPU 输入准备阶段完成，全部策略共享。720p 共 3,600 个 tile，计划不超过 4,096 单元；每个 CTA 按冻结表执行完整 tile，无原子任务领取，无跨组忙等。

原作者训练相机按排序 ID 的模 4 划成 dev0/dev1/test0/test1。每场景只用 8 张开发相机形成平均 tile 列表权重和三等分类；另有独立开发 pilot 决定进入固定确认分支。研究用测试相机与校准相机不重合，但不是原模型训练意义上的 novel views，不报告 PSNR/质量提升。

W1 在 321×181 边界视口、1280×720 各执行 16 帧连续资格，每个参考 Native 重复 3 次；color、final_T、n_contrib 完整字节一致。mapped tile visit 计数均为 1。最初真实视图没有空 tile，另建仅正确性用的相机平移 fixture，16 帧中空/非空交替；两分辨率均验证空像素 final_T=1、n_contrib=0，无状态残留。该 fixture 不混入正式计时。原始 Native 未被改成候选执行结构。

![真实渲染输出](figures/render_examples.png)

图中是每场景首个成功正式块的首帧，固定选择规则，不按性能选样。正式运行每帧做共同轻量全输出摘要，首/中/末帧保存完整结果；事后审计 48 块的全部保存样本，N/R/M 字节一致；每策略末尾另有完整参考检查。摘要用于筛查，不能替代前述完整资格。

W2 保留 SNAP 原始边记录：ca-GrQc 5,242 行 / 28,980 记录，web-Google 875,713 行 / 5,105,039 记录；没有合成扩增。节点 ID 确定性压缩、按行排序。邻接值为 1，32 个请求向量取整数值 0…31，行和小于 2^24，因此 FP32 全部结果可用 CPU 位级比较。两条请求序列是这 32 个输入的不同循环起点，不能视为 1,024 个独立问题。已验证 cuSPARSE、普通 warp-row body、所有冻结映射的完整输出。正式 N 使用预先选择的 cuSPARSE 默认 SpMV；同 body Native 只在初始资格中另外记录，不能把 cuSPARSE 与自写 kernel 的差异全部归因于调度。实际 cuSPARSE version 编码 12508。

三类程序均用新版 compute-sanitizer 完成有界 memcheck 和 synccheck，6 次成功检查均 0 errors。早期工具注入失败保留为 FAILED，未当作数值通过。

## 有效容量与并发迁移

E2 完成 4 家族 × 3 规模 × 4 模式 × 3 新进程，共 144 sessions / 216 组记录。K0 为有用多链整数计算；K1 写入并读取真实共享 tile；K2 为声明工作集上的实际 cg 加载与校验计算；K3 为真实全量流式读写。所有 Native、全卡 Green、组隔离、组并发模式使用相同逻辑任务。每项 32 次预热、128 次测量，完整 CPU 参考与最终输出一致；没有空转或声明大数组但仅触及小片段的伪工作集。

布局按事先固定轮转分配，small 对应 G1、nominal 对应 G2、large 对应 G3；因此本表不是 size×layout 的全因子设计，不能把规模效应与布局效应完全拆开。隔离与并发的同格比较有效，跨格因果解释受限。

{table(['家族','规模/布局','并发组1/组0 每SM容量比 ± 样本SD','组0并发/隔离','组1并发/隔离'],capacity)}

![有效容量](figures/03_capacity.png)

## 唯一候选与完整机制基线

算法为 p(t,g)=work(t)/rate(g,class(t)) 的标准贪心 minimax，最多三类；CTA 数固定取实际 occupancy 的 1 倍，未额外搜索 2 倍。M 使用并发校准速率，R 使用相同日志聚合出的单速率，L 使用同开发权重和 SM 数，I 拓扑盲、S 空间顺序、P 固定置换。T 无物理证据，保留 NA。G2 的 P 先按 SM 数归一化再置换类型速率，保留完整任务集和实际组容量，不简单交换不等份额列表。任务数量/类别/权重分布见 `derived/t10/plan_work_distribution.csv` 和 E3 的完整 task_map。

W1 的 M/R 表重合率约 53%–54%，说明实际表不同，但不同并不等于算法有用。W2 同样冻结表及哈希。所有 E3 已加载 task→group 与冻结表逐项一致；应用运行使用同一计划文件，资格完整验证 exactly-once。应用没有逐 tile 的实际 SM 轨迹，不能提出细粒度物理放置主张。

{table(['E3条件','M/N 时间比 [95% CI]','M/R 时间比 [95% CI]'],e3rows)}

![全机制基线](figures/04_mechanism_baselines.png)

图 4 以 Native=1 表示全部已运行策略，T 的缺项为 NA；原生基线始终保留。d1/l1 的机制增益被单速率 R 解释，其他小的 M/R 改善不能抵消 Native 退化。

{table(['预测模型','独立组记录','有符号误差中位数','绝对相对误差中位数'],modelrows)}

预测为 E2 校准对 E3 独立数据的迁移。R 的标量速度先归一化为均值 1，保留任务权重的毫秒单位；共同缩放不改变原 R 分配。模型只预测组内 kernel event 区间，不预测主机启动/同步成本。M 也未把误差消除。

![模型与并发迁移](figures/05_model_error.png)

## 真实应用的固定确认

E4 每程序 2 输入 × 2 序列 × 6 进程块 × 3 策略，合计 48 进程 / 144 sessions / 73,728 测量帧或请求。每个策略单独预热至少 128 次且至少 1 秒，再记录 512 次；同块共享已分配资源，N 在首位，R/M 固定种子随机次序。全部 48 块完整，没有删去不利值或补选有利样本。

主指标为 CPU 输入提交至 GPU 结果可用的时间，包含相机/向量输入、完整上游、组 launch、context 切换和 join。对 Green 不把跨 context 的 event 当作完整流水线时间；表中主比较始终使用 CPU-ready。W1 render_ms 对 Green 为最大组内 event，不是完整 makespan。共同输出摘要、CSV 写入、部分完整读回和显存查询在主计时外，仍可能影响下一帧缓存；未做 E5 记录扰动消融。

{table(['输入','N 均值 ms','R 均值 ms','M 均值 ms','M/N [95% CI]','M/R [95% CI]'],results)}

均值列是 12 块的算术均值，时间比是条件等权的块内对数比均值，故不是均值列的简单商。每条件内以进程块重采样 20,000 次，固定 seed=2026101403；不重采样像素/帧，不跨设备池化。

W1 两主比较的 97.5% 边际区间为 M/N {ci(stats['W1_M/N'],'ratio_ci97_5')}、M/R {ci(stats['W1_M/R'],'ratio_ci97_5')}；W2 为 {ci(stats['W2_M/N'],'ratio_ci97_5')}、{ci(stats['W2_M/R'],'ratio_ci97_5')}。这提供每个预声明程序聚合内两比较的 Bonferroni 联合 95% 覆盖；表中各输入 95% 区间仅描述性，不是多个 cell 的家族校正确认。

![真实应用结果](figures/06_application_results.png)

| 范围 | 321×181 | 1280×720 | 1920×1080 / 扩大规模 |
|---|---|---|---|
| Bonsai、Train | 位级资格；非性能结论 | 全动态正式确认 | NOT_TRIGGERED |
| 空/非空切换 fixture | 位级资格 | 位级资格 | NOT_RUN |
| Truck | NOT_RUN | NOT_TRIGGERED，未进入校准/测试 | NOT_RUN |
| ca-GrQc、web-Google | 分辨率不适用 | 真实输入原规模独立算子 | NOT_TRIGGERED |

## 成本、生命周期与失败记录

{table(['M 输入','计划加载+上传均值 ms','计划字节','dispatch CPU ms','W1平均总使用显存 MiB'],costtable)}

W1 dispatch_cpu_ms 从进入 dispatch 到 join 返回，其中包含等待上游完成的部分，**不能再与完整 upstream_ms 相加**，也不能称为纯调度额外成本。W1 主计时包含这个等待，属于真实执行路径。未独立记录所有 setup/拷贝/同步子调用时长，因此不能做不存在的精确阶段归因。

最终正式构建耗时分别为：{'; '.join(b+' '+str(round(m['compilation_ms']/1000,3))+' s'for b,m in builds.items())}。每个 build.json 保存配方与源码/二进制哈希，失败构建日志同样保留。原首次 CPU 计划生成未计时，context setup 没有单独分离；这些记为 NOT_INSTRUMENTED，而非 0。另做纯 CPU 事后重建，每个 M/R 表重建 3 次，共 24 张均与冻结表逐项一致；M 重建约 6–24 ms，详见 `plan_reconstruction.csv`。这是新测的重建成本，不代替未知的首次规划时间。

若生命周期额外初始化成本为 C，N 次执行的候选额外成本为 C+N×(tM−tN)。取 N=1/100/1000/10000 时，在已观测点估计退化的输入上都不能得到正回本；web-Google 的差异不确定，也不能给出确定回本帧数。相机正常移动使用冻结 SCENE_PLAN；分辨率、CSR、分配变化应重新生成计划，相关失效/重分配实验属于 E5，NOT_TRIGGERED。

以下只是使用表中算术均值的生命周期点估计，不是新的 E5 实测；C 未完全分离，web-Google 尤其应结合宽区间理解。

{table(['输入','N=1','N=100','N=1000','N=10000'],lifecycle)}

![在线与初始化成本合同](figures/07_cost_contract.png)

累计串行 GPU worker 保留时间 **{cost['worker_seconds']:.3f} 秒（{cost['worker_seconds']/60:.2f} 分钟）**，包括进程内 CPU 输入/参考计算，不等于 GPU 忙碌时间；构建和下载不在该计数内。用户明确本地自有资源免费，记录资源租赁费 **0 CNY**，电费未计量，不能声称总能耗或电费为零。显卡已释放，无后续长 GPU 任务。

{counts}

失败与缺项：旧 sanitizer 4 次注入失败，新版官方 12.8.93 修复后通过；renderer 构建遇 CUDA/CUB 头文件版本冲突，锁定 CUB/Thrust 1.17.2 后通过；sparse 初次构建与 empty fixture 初次链接的诊断均保留。预选 SuiteSparse bcsstk18/pwtk 文件端点 TLS 失败，未反复更改网络；在任何 W2 性能计时前登记改用两个真实 SNAP 输入。W1 缺语义一致的 gsplat Bext，因此不称 Graphdeco 为最快生产后端。

必须保留的设计偏差：E3 各策略实际是新进程，按随机批次配对，未共享同一分配进程；E4 修正为同进程共享缓冲。有限确认只有首 N、无计时尾 N 锚，无法量化块内漂移；R/M 次序已随机，但 N 对比仍有顺序影响风险。校准、资格和正式 host 仪表版本有不同 build cohort，正式数据各程序内部同一 cohort。没有替换日志或事后隐瞒这些偏差。6 块、单器件及 DVFS 条件限制外推，结果不构成严格架构因果实验。

正式微实验、renderer、sparse 的对应源码快照已全部核对哈希。早期 renderer 资格/校准 host 版本未完整独立快照，虽有 build 哈希与原始记录，不能承诺精确重建那一历史 host；此项保留为早期可复现性缺口。

## 双平台与相关工作

![双平台范围](figures/08_platform_scope.png)

`combined_review.json` 只装入本机真实摘要，状态 REVIEW_REQUIRED，明确缺 RTX 5070 Ti；没有伪造第二份数据，也没有远程操作另一台机器。协议、方法、输入哈希全部保留供独立机器比较，兼容哈希不等于因果证明。RTX 5080 历史数据未混入本轮。

Fan 等的 [arXiv:2609.24270v1](https://arxiv.org/html/2609.24270v1) 已研究 cluster/L2 拓扑与调度；本轮 T10 普通 CTA 结果不能复现或否定其 H200/B200 结论。静态持久任务分配本身不是新增贡献。S8 的 ICS 2015 SM-centric 工作已核对引用但未取得全文，保留 LITERATURE_GAP；[OO-VR](https://arxiv.org/abs/2001.03537) 的 NUMA 多 GPU 渲染也不是本轮单卡同一研究范围。当前不作“首次”或完整查重完成的主张。

![主张与证据](figures/09_claim_evidence.png)

下一步投入判断：完成本轮测量和可复现负结果记录，不进入 E5 追加场景/常量/共置搜优。若独立第二平台已有结果，可按原 merge 工具并列审查；只有发现不能被 R/原生调度解释的真实增量及明确算法差异后，才值得重新登记后续研究。

## 原始数据入口与复算

- [机器可读平台摘要](platform_summary.json)、[双平台缺口审查](combined_review.json)、[贡献卡](CONTRIBUTION_CARD_t10.md)、[导师简报](MENTOR_BRIEF_t10.md)。
- `../run_index.jsonl`：所有完成 run 的唯一 ID、相对路径、状态、build、配置与 worker 时间；每目录均有 manifest、stdout/stderr、健康快照。
- `../derived/t10/session_summaries.csv`：144 个策略 session 的均值/分位数；`paired_M_N.json`、`paired_M_R.json`：全部独立块的主比较。
- `../derived/t10/capacity.csv`、`mechanism_sessions.csv`、`prediction_error.csv`：容量、完整机制与独立模型误差。
- `../derived/t10/audit.json`：输出样本、计划、二进制/源码、在线合同审计；`execution_costs.csv`、`costs.json`：完整成本记录与缺项。
- `../preregistration`：冻结计划、开发权重、分割及原决策；`../DECISIONS.jsonl`：决策时间线。
- 精简包保留全部小型 CSV 和关键失败证据，大输出按每条件最早成功 run 保留。模型不重复打包，`inputs_manifest.json` 保留来源及哈希。CPU 复算只需 Python 标准库；图表另需 NumPy/Matplotlib。详见 `../REPRODUCE.md`。

主要实现出处：[Graphdeco 固定版本](https://github.com/graphdeco-inria/diff-gaussian-rasterization/tree/59f5f77e3ddbac3ed9db93ec2cfe99ed6c5d121d)、[CUDA 12.8 Green Context 文档](https://docs.nvidia.com/cuda/archive/12.8.0/cuda-driver-api/group__CUDA__GREEN__CONTEXTS.html)、[NVIDIA cuSPARSE 示例](https://github.com/NVIDIA/CUDALibrarySamples/tree/07c4f09223302ce4310eef945ed458e092598d17/cuSPARSE/spmv_csr)、[SNAP ca-GrQc](https://snap.stanford.edu/data/ca-GrQc.html)、[SNAP web-Google](https://snap.stanford.edu/data/web-Google.html)。下载与原始依赖许可随导出清单保留。
'''
 (P/'DUAL_TOPOLOGY_PAPER_REPORT_t10.md').write_text(report)
 card=f'''# 贡献卡：T10 实测

研究问题：公开可控资源组的类型化服务率，能否在完整执行成本下超过 Native 与同信息单速率 R？

最接近已有工作：Fan 等拓扑/调度研究、SM-centric 任务分配、普通加权均衡和持久 CTA。全文查重尚有 S8 缺口。

已知的方法：静态表、三类速率、贪心 minimax、occupancy 限制。我们新增的具体算法能力：**本轮没有证据支持独立算法创新**；贡献是受控实现与可复查实测。

与同信息简单基线的区别：M 保留 class×group 速率，R 聚合为 group 单速率；共享校准日志、输入权重与执行器。W1 M/R 表重合约 53%–54%，但表不同并未形成部署增量。

独立实验：E3 252 sessions；E4 48 进程块/144 sessions，全部 ID 见 run_index。物理证据等级：公开 Green 资源集 + 实际逻辑 SM 覆盖；无 GPC 图、无 floorsweeping 因果结论。

本机主要比较（时间比，低于 1 为改善）：

{table(['范围','M/N [95% CI]','M/R [95% CI]'],[[w,ci(stats[w+'_M/N']),ci(stats[w+'_M/R'])]for w in ['W1','W2']])}

两个平台：仅 T10 实测；RTX 5070 Ti 未运行，不合并原始毫秒数。跨程序：完整动态 3DGS + 真实 CSR 算子；后者是新适配器，不是既有完整生产应用。

完整成本：主指标计入启动/同步/context 切换；在线规划为 0，但执行器非零。首次 CPU 规划和独立 setup 未计时，启动回本不可精确计算；正式平均时间不支持部署回本。

未解释条件：短任务容量偏差、web-Google 的宽区间、单器件 DVFS/顺序漂移；有限确认无计时尾 N，E3 使用新进程批次。Train 对 R 的约 0.5% 改善仍慢于 N。

论文最弱一环：无超过 N 与 R 的一致真实增量，也无已证明的新算法能力；第二器件/生产应用/强生产 renderer 仍缺。

最终判断：**{outcome}**。保留可复现负结果，不将本轮包装为通用性能论文，不追加 E5 搜优。
'''
 (P/'CONTRIBUTION_CARD_t10.md').write_text(card)
 brief=f'''# 导师简报：T10 计算拓扑实验

本轮已完成可支持的有界实验和独立确认；结论是 **{outcome}**，不支持目前的方法作为通用加速论文。这里仅观测公开资源组，没有证明芯片裁剪的物理因果机制。

设备实测 56 SM、4 MiB L2，Green 28+28、18+38 可用；cluster 不支持。144 次容量实验、252 次机制实验，以及 48 个正式进程块全部完成。73,728 帧/请求的在线输出筛查通过，资格和保存完整样本位级一致；6 次新版 sanitizer 检查 0 errors。

{table(['输入','M/N [95% CI]','M/R [95% CI]'],[[w+'/'+n,ci(stats[w+'/'+n+'_M/N']),ci(stats[w+'/'+n+'_M/R'])]for w,n in names])}

时间比小于 1 才是改善。W1 合并 M 相比 Native 慢约 {(stats['W1_M/N']['ratio']-1)*100:.1f}%；M 与 R 总体相近。Train 上约 0.5% 的 M/R 改善已保留，但没有 Native 增益；大图 CSR 区间较宽。E3 有一个机制条件比 Native 快，但 R 同样能解释，不能写为类型化方法的新贡献。

工作产物可用于复查和负结果研究：源码、冻结计划、真实模型/图来源、全部小型原始记录、失败日志、配对 bootstrap、9 张结果图、机器摘要和精简复算包。资源租赁费 0 CNY；串行 worker {cost['worker_seconds']/60:.2f} 分钟，电费未计量。

边界：1 张 T10；没有 RTX 5070 Ti 实测；W2 是真实输入独立算子而非完整既有应用；6 块探索性；有限确认无计时尾 Native；E3 为新进程批次；首次规划/setup 分离成本未计时。E5 根据预定规则未触发。

建议当前停止在此方案继续选场景。若继续论文，先明确一种能超越同信息 R 的算法能力，再预登记独立第二平台与真实生产应用验证。不要把“不同的任务表”“局部 event 更快”或“弱基线改善”写成新方法贡献。
'''
 (P/'MENTOR_BRIEF_t10.md').write_text(brief)
 print('Report, contribution card, mentor brief and machine summaries generated.')
if __name__=='__main__':main()
