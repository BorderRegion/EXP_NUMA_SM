"""Assemble a Chinese report from audited aggregates, without hiding NA cells."""
import json,math
import numpy as np
from common import *
r=runroot()
def load(name):
 p=r/'derived'/f'{name}.json';return json.loads(p.read_text()) if p.exists() else {}
p1=load('P1_SUMMARY');fine=load('FINE_SUMMARY');native=load('NATIVE_ANALYSIS');micro=load('MICRO_ANALYSIS');life=load('LIFECYCLE_ANALYSIS');runtime=load('RUNTIME_SUMMARY');audit=load('COMPLETION_AUDIT');rules=load('RULE_SCOPE_AUDIT')
complete=audit.get('status')=='COMPLETE_WITH_EXPLICIT_NA'
def effect(z,scale=1,center=0,digits=3):
 v=z.get('estimate',z.get('mean'));lo,hi=z['ci95'];return f"{(v-center)*scale:.{digits}f} [{(lo-center)*scale:.{digits}f}, {(hi-center)*scale:.{digits}f}]"
def table(header,rows):return ['| '+' | '.join(header)+' |','|'+'|'.join(['---']*len(header))+'|',*['| '+' | '.join(map(str,x))+' |' for x in rows],'']
L=['# NUMA-first V3：T10 实验报告','',f"状态：**{'已结束，缺项与条件式 NA 明确列出' if complete else '执行中；本文是自动更新的阶段报告'}**。生成时间 {utc()}。",'',
f'原始运行目录：`{r}`。输入包 SHA-256：`10fd086b4281c807153fa1f042470707e5401ff2d49d11922cf28d8ce5b0202f`。','',
'## 1. 先说结果意味着什么','',
'本轮把三件事分开：有没有可重复的位置—地址差异；能不能用很短的规则表达并真实控制执行位置；这种规则扣除控制和准备成本后是否更快。第一件事在部分小工作集条件上出现了正证据，但这不自动证明物理 NUMA，也不自动给出应用加速。这里测量的是不同执行位置访问数据的耗时与完整消费时间，没有直接测量 SM-to-SM 通信延迟。','',
'原先把 56 个 SM 粗分为两个 28-SM 组时，预冻结主要确认条件没有稳定的正向地址交互。逐 SM 分析却发现小集合、低并发条件存在可重复结构，因此继续做了事后 2-SM 资源细化，并用独立的新分配确认。没有把粗分组的阴性结果写成“整块 GPU 没有非均匀性”。','',
'编译后的合成消费者真正使用公开 Green Context 资源组、算术地址规则和跨组 Graph；N/E/B/T/X/Y/M/P 都实际执行。T 使用同样标定信息、保持原数据布局，是必须战胜的简单基线。应用侧则保留三族成熟原生实现及普通调度对照：尚未在这些活跃应用分配中验证可部署的短公式亲和，因此没有伪造应用 M/T 时间，也没有把探针地图搬给应用。','']
if micro.get('comparisons'):
 primary=[x for x in micro['comparisons'] if x['method']=='M' and x['baseline'] in ['N','T'] and x['metric']=='total_ready_ms'];wins={b:sum(x['ratio']['ci95'][1]<1 for x in primary if x['baseline']==b) for b in ['N','T']};losses={b:sum(x['ratio']['ci95'][0]>1 for x in primary if x['baseline']==b) for b in ['N','T']}
 L += [f"{'最终' if complete else '当前'} 9 个合成条件中，M/N 的区间完全低于 1 有 {wins['N']} 个、完全高于 1 有 {losses['N']} 个；M/T 分别为 {wins['T']}、{losses['T']} 个。这里每项用 97.5% 探索性区间，9 条件全部展示；这不是跨条件择优后的确认性显著性声明。",'']
L += ['## 2. 运行条件与预算','',
f"设备为本机 T10，56 SM、4 MiB L2、15 GiB 显存，驱动 580.178.04。新账本累计 **{runtime.get('worker_hours',0):.3f} / 24 GPU-worker 小时**；旧实验时间不混入。worker 时间含锁内 CPU 准备、参考校验和 conditioning，不是 GPU busy time，也不是整段研究墙钟时间。",'',
'保持已有 100 W 请求/执行上限、风扇、过温、低转速与看门狗保护；未修改系统服务、驱动、功耗配置或时钟。100 W 是设备支持的最低上限；更高第二条件没有实施：本轮未建立第二套带权限的管理配置，免密 sudo 检查失败；应用 T/M 的部署前提也未成立，故相应矩阵记 NA。这是未执行项，不是声称硬件不支持更高上限。没有取消保护，没有使用或保存口令。按本轮离线约束，没有下载模型/依赖、安装软件或启用远端设备。','']
ag=runtime.get('aggregate',{})
if ag:
 L += table(['所有已结算 worker 的 1 Hz 样本','最小','中位','95% 分位','最大'],[[label,*[f"{ag[k][q]/scale:.2f}" for q in ['min','median','p95','max']]] for k,label,scale in [('temperature_c','温度 °C',1),('power_mw','采样功耗 W',1000),('sm_mhz','SM MHz',1),('mem_mhz','显存 MHz',1)]])
 L += [f"请求上限读数为 {ag['requested_cap_mw']} mW，执行上限读数为 {ag['enforced_cap_mw']} mW。{ag['above_reported_cap_samples']} 个功耗样本高于同次读到的上限；尖峰未删除，未独立诊断其物理或传感原因。NVML 字段依次查询，非原子采样；不能把本轮称为固定实际功耗或固定频率实验。",'']
L += ['每个正式整块先做 180 秒代表负载 conditioning，随后按固定序列运行该块内全部 case。此处的 block 是整套 case 的 superblock，而不是每个子进程；这是明确的预算口径偏离。所有实验 worker 共用文件锁串行，但桌面服务仍在 GPU 上，不声称整卡只有实验进程。结果没有按温度、频率或快慢删块。','',
'仅清理可再生成的软件缓存以保留磁盘余量，未删模型或既有实验；详见 CACHE_CLEANUP.json。机器资源费用按用户说明记 0，未计量电费。','',
'## 3. 原始位置—地址证据','',
f"P1：6 次主分配（2 开发 + 4 确认），96 strata，{p1.get('record_count',0):,} CTA 记录，{p1.get('epoch_count',0):,} epochs。消费尺度 2/8/32/128 MiB，普通与 .cg load，低/高并发，6 种消费模式和 4 种缓存干预。随机任务排列用于诊断，不是候选调度 LUT。原始图、缺格与全部 384 条件均保存。",'',
'预冻结主要条件：自然缓存、.cg、高并发、coalesced one-pass。下表是 4 次确认分配的 late signed log interaction ×100；这是局部 CTA 对比，不是应用提速百分比。','']
if p1:
 z=[x for x in p1['confirmation_conditions'] if x['cache']==0 and x['cg']==1 and x['concurrent']==1 and x['mode']==0]
 L += table(['工作集 MiB','局部 signed log effect ×100 [95% CI]','组残差前后轮相关 [95% CI]'],[[x['bytes']>>20,effect(x['late_signed_log_effect'],100, digits=5),effect(x['early_late_group_residual_correlation'])] for x in z])
L += ['单 SM 的例外不能被组均值掩盖：2 MiB、低并发、.cg、repeat4、owner-C1 条件的早晚轮 SM×地址残差相关约 0.905（区间约 0.844–0.951），但共同覆盖仅约 27.85%，约 16 个 SM，且为全条件检查后发现。它支持继续研究缓存尺度的经验差异，不识别物理 home；完整排名和相反效应同样保留。','',
'原探针通用除法/取模在 SASS 中包含倒数指令，可能稀释访存影响。因此没有重写原 P1 数据，而是新增等价移位/掩码版本，保存 CPU 地址等价验证、SASS 和 memcheck，再重新测量。两份粒度 scout 使用额外新分配，不冒充原主分配内的粒度留出；依赖链只触及 256-step 前缀，实际唯一集合约 0.5 MiB，不能把请求分配容量称为该链的实际消费集合。','',
'### 2-SM 细化分支','',
'28 个公开 2-SM 组覆盖实际 56 SM；用早轮、32 个 fit 区域选最多 6 bit 的 parity 规则及等量分组，另 32 区域和晚轮检验。下表仅用移位版本的 3 次独立确认分配，第一份开发分配排除。它是事后扩展，不与原 P1 预冻结确认混池。','']
if fine.get('conditions'):
 z=[x for x in fine['conditions'] if x['control_scope']=='BALANCED56SM' and x['cache']==0 and x['cg']==1 and x['mode']==0]
 L += table(['工作集 MiB','全组地址残差相关 [95% CI]','晚轮 signed log effect ×100 [95% CI]'],[[x['bytes']>>20,effect(x['map_stability']),effect(x['late_effect'],100)] for x in z])
 z=[x for x in fine['cross'] if x['control_scope']=='BALANCED56SM' and x['cache']==0 and x['mode']==0]
 L += table(['MiB','存储 layout','真实组交换 log(reverse/match)×100 [95% CI]'],[[x['bytes']>>20,x['layout_swap'],effect(x['effect'],100)] for x in z])
L += ['真实交换的效应可能远小于、相反于或比局部标定更嘈杂；所有缓存状态、布局交换及同 payload 的 2×2 单元都保留。新分配可能复用物理页，独立 allocation 不等于证明获得独立物理地址。','',
'## 4. 编译产物与八策略','',
'选择公开资源限制入口。初始化选择并合并两个各 28-SM 的计算集合，记录实际 SM roster；以 parent stream fork/join 捕获 Graph，稳态一次 host Graph launch，N 一个实质数学 kernel，其余两个。没有独立规划 kernel，也没有普通 grid 的自旋 barrier。Graph 能力已在本机独立资格测试，不照搬在线 API。','',
'地址类为 `parity(region & MASK) XOR BIAS`，MASK 非零且至多 6 个 bit。插位 slot 是 CTA 不变的线程序言表达式，放在 payload 循环外；SASS 部分使用 uniform 指令，但 POPC 仍写普通寄存器，不能声称全 CTA 仅一次硬件执行。内部访问为固定 4 KiB 窗口移位/掩码，coalesced load 保留。数学双射保证两个类各 32 个 region、无重叠且覆盖全体；它不会创造 NUMA。kernel 为 20 registers/thread、1036 B shared、无 spill 的本地编译记录；SASS 不含原通用除法的 MUFU.RCP。标定常量是标量 launch 参数，并非每个 mask 都重编译 cubin，不宣传常量全部成为机器立即数。','']
L += table(['策略','实际操作'],[['N','单 kernel，全 56 SM，原布局的相同合成数学体；不是生产库应用 N'],['E','中性 28+28 SM 组、原布局、连续逻辑半区'],['B','中性组、原布局、普通偶/奇 region 分配'],['T','学习组与 parity 任务分配，保持原数据，无着色搬移'],['X','学习组、原数据、连续逻辑半区'],['Y','中性组、算术着色布局'],['M','学习组 + 算术着色布局'],['P','M 相同存储与任务量，反转计算组匹配']])
L += ['T/M 是不同逻辑布局的独立测量，不重复充当别名样本。但在本均匀 reduction 中，二者所访问的物理地址集合相同；只有逻辑关联/输出位置表达和布局成本不同。这显著限制新颖性主张：不能仅凭“编译”二字称为超越简单静态分配的新算法。','',
'只存一份 GPU 数据布局；CPU 原布局/着色布局用于实验重置，生成和上传分别计时。每策略在 warm-end、请求 0/64/127、batch-end 保存全部 64 个逻辑和与 SM 记录，CPU 独立重算输出并核对分组。128 个请求并非逐个保存所有中间值；完整 batch 也不被当成独立重复。','',
'经验类别只覆盖本活跃 allocation 中采样的虚拟 anchor，子区域真实 home 未测，物理 home 已知比例为 0。RULE_SCOPE_AUDIT.json 给出空间留出上的经验符号一致率，不能称为物理 home 分类准确率。','',
'## 5. 编译合成负载：完整成本边界','',
'3 工作集 × 3 消费状态 × 8 策略 × 8 独立分配块，正式主策略采用任务包的 8 阶 Williams 顺序，平衡每个位置和全部 56 个有向相邻策略对，另有 N 首尾锚点。开发版原为循环顺序；在任何正式 phase 开始前修正并重新资格验证，原 host 源码/二进制和开发数据保留，GPU cubin 与重复次数不变。每 phase 至少 64 次且 150 ms 事件跨度 warmup，128 次 output-ready 请求，吞吐重复数由开发 N 冻结并对所有策略固定。scratch 干预 128 MiB，由 SM 实际扫描；它不是保证 flush。','',
'下表为 M 相对基线的 total-ready 时间变化百分比 `(时间比−1)×100`，负数更快；包括显式 scratch 准备。M/N、M/T 各用 97.5% bootstrap 区间，针对每个 case 的两比较；不是 9 条件整体确认性区间。','']
if micro.get('comparisons'):
 z=[x for x in micro['comparisons'] if x['method']=='M' and x['baseline'] in ['N','T'] and x['metric']=='total_ready_ms'];L+=table(['MiB','状态','比较','时间变化 % [97.5% CI]'],[[x['bytes']>>20,['HOT one-pass','SCRATCH one-pass','HOT repeat4'][x['mode']],f"M/{x['baseline']}",effect(x['ratio'],100,1)] for x in z])
if micro.get('bstar_comparisons'):
 L+=['在第一轮正式 phase 开始前，另用唯一开发块的 total-ready 均值冻结 B*：选择 B/T 中较快者。它只是已有策略的参照标签，不新增策略或独立样本；原 B、T 结果始终保留，主比较仍为 M/N 与 M/T。','']
 z=[x for x in micro['bstar_comparisons'] if x['metric']=='total_ready_ms'];L+=table(['MiB','模式','B* 选定参照','M/B* 时间变化 %','所复用区间置信度'],[[x['bytes']>>20,x['mode'],x['selected_comparator'],effect(x['ratio'],100,1),f"{x['ratio']['confidence']*100:g}%"] for x in z])
if micro.get('comparisons'):
 L += ['下表保留执行组织、中性任务分配、仅计算、仅布局、联合与反向的全部九个条件，均为 total-ready 时间变化。E/N 检查采用两个分支本身的组织代价；M/E 检查增加学习信息及布局后的总差异；P/M 检查反转匹配是否产生一致惩罚。X/Y 也分别与 N 比较。这里用未作多比较调整的 95% 探索性区间，不与主比较的 97.5% 区间混淆。','']
 rows=[]
 for size in [2<<20,8<<20,32<<20]:
  for mode in range(3):
   cells=[]
   for method,base in [('E','N'),('B','N'),('X','N'),('Y','N'),('M','E'),('P','M')]:
    z=next(x for x in micro['comparisons'] if x['bytes']==size and x['mode']==mode and x['method']==method and x['baseline']==base and x['metric']=='total_ready_ms')
    cells.append(effect(z['ratio'],100,1))
   rows.append([size>>20,mode,*cells])
 L+=table(['MiB','模式 0热/1干预/2复用','E/N %','B/N %','X/N %','Y/N %','M/E %','P/M %'],rows)
L += ['所有 E/B/X/Y/P、事件时间、batch 均摊、绝对毫秒差以及逐请求原值均在 MICRO_ANALYSIS.json 和原始 samples.csv。CPU-ready、GPU event span 与紧密 batch 不互换；每请求 p99 只作块内描述。8 个独立块仍是小样本，所有区间均为探索性。没有用时钟回归修正成更好的结果。','',
'## 6. 三族原生应用与负例','',
'正式原生矩阵为 20 个条件 × 8 整块：Bonsai/Truck × 1080p/1440p × 两相机序列（8）；ca-GrQc/web-Google × RHS1/16（4）；grouped GEMM 四形状与 decode attention 四形状（8）。P2 另有 Train/Bonsai 和三整块开发盘点。每个 case 的字节、形状、准备、节点、正误检查、时间和未知项见 BOTTLENECK_CARDS.md。','',
'渲染保留原生 preprocess/binning/sort 与动态帧、HOT 快照和 scratch 快照。每状态至少 128 帧且 2 秒 warmup、256 测量帧。Bonsai 1080p 的 tile 候选列表颜色起始地址覆盖的虚拟 4 KiB 页数中位约 372，Train 约 1018；统计未展开跨页的 12-byte 属性，也未跟踪 early-stop/条件加载，所以不是实际消费页数或硬件流量。这是布局结构代理，不能据此声称多物理 home。未拆分像素的 Gaussian 累积顺序。实际 raw color/T/contrib 保留，预览是保存结果的显示，不是生成图。','',
'稀疏保留真实 CSR 结构、一般值与 cuSPARSE，含相同 x producer copy，double 参考；只拥有两张本地已见图，不称新图留出。grouped/decode 用一般可复算输入和 FP64 参考，是算子机制测试，不是完整 LLM。grouped 同体 CORE/Q1 原始位比较；库数学差异按冻结数值合同验收。','',
'已有 Q1-minimal 是普通调度对照。下表 HOT 的 batch 时间比 >1 表示比 cuBLAS 慢；即使 Q1 Graph 的实质 GEMM kernel 数更少，也必须报告这个差距。','']
if native:
 z=[x for x in native['comparisons'] if x['stage']=='P4' and x['state']=='HOT_SLOT0' and x['method']=='B_Q1_MINIMAL' and x['metric']=='batch_per_request_ms'];L+=table(['配置','Q1 / cuBLAS [95% CI]'],[[x['case'],effect(x['ratio'])] for x in z])
L += ['原生算子的真实 Graph 节点通过保留 graph 的公开 driver API 读取。Kineto 对部分 Graph 产生空/不完整 trace，不能据此认定 0 kernels。代表 native renderer 的 runtime 与 driver launch 计数重叠，不相加。','',
'P2/P4 相机有偏离：执行器实际选择 `camera_index % 4 == 2 + sequence`，不是准备清单所写的 dev0/1；Bonsai q0 在 P2 与 P4 重叠，Truck 与 q1 提供不同输入，但不能把全 P4 称独立相机留出。均使用原训练场景相机，未声称新视角质量泛化。','',
'应用 E/T/X/Y/M/P、每族融合×映射四格和第二功耗矩阵均为明确 NA。原因是缺少活跃应用分配上的可表达亲和，及第二功耗权限条件，不是“跑过但没有收益”。因此本轮既不证明渲染负载不适合 NUMA，也没有交付真实应用的 NUMA 加速。','',
'## 7. 初始化、回本与真实分配生命周期','',
'研究探测、编译/源审计、设备初始化、分配标定、host 着色、layout upload、Graph build 分开记录。micro 的 calibration_total 已包含拟合与合并 context 创建，不能再重复相加。M/N 增量估计含 28 个 fine group 支持、标定、着色、copy/Graph 差额；M/T 共享标定，只计算新增布局与差额。module load 未单独隔离，这不是完整真实应用部署成本。','']
if micro.get('synthetic_break_even'):
 rows=[]
 for size in [2<<20,8<<20,32<<20]:
  for mode in range(3):
   for baseline in ['N','T']:
    z=[x for x in micro['synthetic_break_even'] if x['bytes']==size and x['mode']==mode and x['baseline']==baseline];extra=np.mean([x['incremental_observed_setup_estimate_ms'] for x in z]);saving=np.mean([x['ready_saving_ms'] for x in z]);b=math.ceil(max(0,extra)/saving) if saving>0 else '不回本（均值未更快）';rows.append([size>>20,mode,'M/'+baseline,f'{extra:.3f}',f'{saving*1000:.3f}',b])
 L+=table(['MiB','模式 0热/1干预/2复用','比较','增量准备 ms 均值','每请求节省 us 均值','按这些均值的回本请求数'],rows)
 L+=['回本数是观测均值的描述性计算，未传播置信区间，不保证将来回本；单块正负及完整成本值均保留。若稳态均值更慢，不能靠无限摊销解释成收益。','']
L += ['生命周期在每块同一个 primary context 内，实际申请 2 MiB → 释放并重新申请 2 MiB → 释放并扩容到 8 MiB；上代 Graph 销毁、buffer 释放后才开始下一代。即使 VA 相同也增加 generation 并重新标定，不使用已释放指针或旧规则。4 块 ×3 事件 ×N/T/M=36 个正式主 session，另有 N 锚点。旧合并 Green Context 句柄在该进程结束时统一销毁，三个事件中合并组数量有界增加；所以跨事件差异不只反映容量变化。','']
if life.get('summary'):
 L+=table(['事件','方法','output-ready us [95% CI]'],[[['首次2MiB','重申请2MiB','扩容8MiB'][x['event']],x['policy'],effect(x['ready_ms'],1000)] for x in life['summary']])
 L+=table(['事件','比较','output-ready 时间变化 % [95% CI]'],[[['首次2MiB','重申请2MiB','扩容8MiB'][x['event']],'M/'+x['baseline'],effect(x['ratio'],100,1)] for x in life['comparisons'] if x['metric']=='ready_ms'])
 L+=table(['事件','标定 ms 范围','相同 VA 次数/4'],[[event,f"{min(float(x['fit']['calibration_total_ms']) for x in life['events'] if not x['qualification'] and x['event']==event):.3f}–{max(float(x['fit']['calibration_total_ms']) for x in life['events'] if not x['qualification'] and x['event']==event):.3f}",sum(x['identity']['same_virtual_address'] for x in life['events'] if not x['qualification'] and x['event']==event)] for event in range(3)])
L += ['生命周期只证明合成编译消费者在这些事件上的处理与代价；没有测真实模型 KV append、renderer 场景替换或 production graph update。显存列出的 allocated/reserved 不相加；scratch、输入槽、参考张量和 context 支持不是免费内存。所有分配检查保留至少 max(2 GiB,15%) 的设备余量。','',
'## 8. 论文可以说到哪里','',
'可复核的产出是：在 T10 上区分粗资源组阴性与细 SM/cache 尺度的正结构；用公开资源组与实际 Graph 完成无任务 LUT 的算术映射对照；测量强简单基线、布局与重新标定的成本。实验范围和缺格使结论可被反驳，而不是只报最佳值。','',
'目前不能声称发现 T10 的物理 NUMA 拓扑、破解物理地址 hash、测得远端延迟、三族应用加速，或已证明论文新颖性。静态任务分配、布局/持久执行和 grouped visitor 并不是本工作独有；T/M 在均匀 reduction 中物理地址集合相同尤其需要审稿人质疑。','',
'输入包 docs/08_EVIDENCE_AND_RELATED_WORK.md 提供了前人文献与 NVIDIA 文档摘要。本轮按离线约束未下载或重新核验这些全文；只把它们作为用户提供的设计背景，不能伪称完成独立系统文献综述。真实 API/ABI 的使用以本机头文件、编译和执行结果为准。','',
'## 9. 复算、完整性与恢复','',
f"覆盖审计：`derived/COMPLETION_AUDIT.json` 状态 `{audit.get('status','NA')}`。保存了一个最初 renderer 资格失败（CPU CUPTI 回调错误），修复后重做资格；失败源/二进制/日志保留。两个外壳排队请求在获取 GPU 前退出，已归档 manifest 并恢复有限独立进程，没有重跑或删除成功块。",'',
'每个 worker 有命令、时间、source/binary SHA、环境、原始输出、设备前后快照与 1 Hz 日志。Git 基础提交在实验期间不变，新源码以 SHA 与编译快照绑定，不能单靠旧 Git HEAD 假称覆盖新代码。外部复用 Q1 二进制和依赖源码单独列在 compiled/EXTERNAL_DEPENDENCIES.json。','',
'小审阅包包含报告、全部汇总/每块数据、源代码、配置冻结、编译/SASS 证据、关键微实验原值、图与 CPU 复算脚本；大 CTA 二进制、原模型与全分辨率 float 图保留本地，不塞入网页版上传包。压缩包不是完整可迁移的 GPU 软件环境。包内 README 给出精确复算命令和未包含项。','',
'最终 RESTORATION_REPORT.json 只读比较保护脚本/服务/功耗配置的前后 SHA，并检查服务、100 W 与实验进程退出。本轮没有硬件配置变更，因此不需要写回旧配置。审阅质疑另见 审阅问题.md；各 NA 的原因和全部覆盖计数见审计 JSON。','']
L += ['主要图在审阅包的 `figures/` 内，本地位于上述运行目录的同名子目录：','',
'- `position_address_original_and_residual`、`individual_sm_missing_cells`、`independent_address_stability`：原 P1 原图、缺格和独立轮次。','- `small_sparse_sm_exception`、`fine_calibration_and_actual_control`、`actual_matching_cross_controls`：事后例外与实际交换对照。','- `compiled_micro_primary`、`compiled_micro_all_controls`、`actual_micro_strategy_order`：完整请求、所有策略与实际顺序。','- `native_render`、`native_sparse`、`native_inference`、`ordinary_q1_control`、`native_render_previews`：原生应用、普通控制与真实保存图像。','- `compiled_lifecycle`、`whole_campaign_telemetry`：重新分配代价及全程温度、功耗、频率。每图有 PNG 和 PDF。','']
(ROOT/'NUMA_FIRST_V3_T10_REPORT.md').write_text('\n'.join(L).rstrip()+'\n')
print('report written',len('\n'.join(L)), 'characters', 'final' if complete else 'partial')
