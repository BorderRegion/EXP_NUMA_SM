from common import *
import numpy as np,gzip,csv,collections
R=RUN/'reports';R.mkdir(exist_ok=True)
comparisons=read(RUN/'derived/COMPARISONS.json');policies=read(RUN/'derived/ALL_POLICIES.json');anchors=read(RUN/'derived/ANCHORS_AA.json');phases=read(RUN/'derived/ALL_PHASES.json')
def find(stage,case,contrast,metric='gpu_per_request_us',view='batch'):
 return next(x for x in comparisons if x['stage']==stage and x['case']==case and x['contrast']==contrast and x['metric']==metric and (stage=='E4' or x.get('view')==view))
def effect(x):
 lo,hi=x['ci95_change_percent'];return f"{x['time_change_percent']:+.3f}% [{lo:+.3f}, {hi:+.3f}]；{x['faster_blocks']}/6 快"
def table(headers,rows):return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']+['| '+' | '.join(map(str,r))+' |' for r in rows])
ledger=[json.loads(x) for x in (RUN/'ledger.jsonl').read_text().splitlines()];seconds=sum(x['seconds'] for x in ledger)
temperatures=[]
for f in (RUN/'raw').glob('*/telemetry.jsonl'):
 for line in f.read_text().splitlines():
  q=json.loads(line)['query'].split(',')
  if len(q)==8:temperatures.append(float(q[3]))
e2cases=sorted({x['case'] for x in comparisons if x['stage']=='E2'});e3cases=sorted({x['case'] for x in comparisons if x['stage']=='E3'})
def e4get(cid,pol,metric,ref='SHARED56'):return next(x for x in policies if x['stage']=='E4' and x['case']==cid and x['policy']==pol and x['reference']==ref and x['metric']==metric)
e4summary=[find('E4',cid,'SPREAD/SHARED56','job_output_ready_us') for cid in ['GQA4_LONG','BATCH4_RAGGED']]
net_positive=all(x['ci95_change_percent'][1]<0 for x in e4summary)
intro='两种前景的分散家族平均，在本轮热态固定混合任务上均快于未分区并发；这仍需结合背景损失、初始化、跨日和固定规则独立确认，不是物理 NUMA 证明。' if net_positive else '本轮不能把同配额下的分散优势，直接升级为已经成立的全资源稳定净加速。原生并发、串行参考与前后台结果必须一起看；没有按事后最快点改变默认方案。'
parts=[f'# T10 真实 GPC 竞争与 GQA 实验报告\n\n运行 `{RUN.name}`；本机 T10 单卡。实验依据附件 20261019 版，E0–E5 的实际完成情况与缺项见审计。\n\n{intro}',
'## 一、读数字的方法与完整范围\n\n本轮统一用 `r = T_candidate / T_reference`，时间变化为 `100 × (r − 1)`，**负数更快，正数更慢**。表内区间均为 95% 探索性整进程块 bootstrap；枚举 6^6 种经验重采样。六块包含事前 TPC 排除轮换，仍只是一张卡，不是六张卡。没有对全部条件或历史 25 阶段作全局多重比较校正。\n\n每个家族先对五种放置取平均 log 时间，再做六块统计；没有用最慢 PACK 作唯一基线。单次 output-ready 与 Graph 批量分列，不把均摊时间叫交互请求 p99。主 phase 各视图保留 64 次完整请求；辅助锚点至少 16 次。每条路径预热至少 32 次且主机执行区间累计至少 50 ms。四输入槽逐个轮换，所有候选使用相同批量长度。所有长尾和负结果均保留。',
table(['阶段','已完成主 phase','说明'],[['E2',len([x for x in phases if x['stage']=='E2' and x['role']=='PRIMARY' and x['view']=='single']),'720 PACK/SPREAD + 72 同体全资源参考；另存单次/批量两视图'],['E3',len([x for x in phases if x['stage']=='E3' and x['role']=='PRIMARY' and x['view']=='single']),'四形状 × 两模式 × 12 策略 × 六块'],['E4',len([x for x in phases if x['stage']=='E4' and x['role']=='PRIMARY']),'两前景 × 14 安排 × 六块；另有 12 个 E56 主体控制'],['E1','CPU 重分析','六个历史进程、每进程两轮、两缓存配方；不重新采样旧矩阵']]),
'\n## 二、实际资源控制与工程差额\n\n本次 RM GET 与历史快照一致：GPC0–5 启用 SM 为 10/12/12/10/0/12。可选 `GR_GET_PHYS_GPC_MASK` 仍返回权限不足，其输出未用于结论；其他成功接口与 CUDA/逐 SM 表交叉核验。没有写私有 RM SET、改屏蔽或改驱动。\n\n公开 CUDA Green API 枚举 28 个两 SM 单元，诊断读取实际 SM 后再按成员合并。66 个轮换/NEUTRAL 集合均核对前景 10 SM、互补背景 46 SM，无交集并覆盖全部 56 SM；各个正式进程重新枚举核验。每块五 PACK 与五 SPREAD 覆盖同样的 50 SM、各出现一次。没有占位 CTA、48 KiB 驻留伪分区或按 blockIdx 猜位置。\n\n原 N19 的未改二进制保留。它的通用源码即便选 DIRECT/BLIND 仍保留无用的 SM 读取/偏好分支；为满足本轮正式路径不读 SM/clock 的约束，新 E56 只移除此未使用路由，保留数学体、网格、W、16B 搬运、归并/写入/复位。新旧入口都测全资源，不能把这个编译/入口差额归为放置收益。正式 32 个 decode 模板的 SASS 未含 SMID/clock，Trace 变体只用于独立诊断。\n\nBLIND 原有双队列和其既有页顺序原样保留并计费；没有启用 MATCH/INVERT/SHUFFLE，也没有新建 task→SM 表。微基准默认向量加载为 `LDG.E.128.SYS`，`.cg` 为 `LDG.E.128.STRONG.GPU`；这不证明某级缓存必命中。',
'\n## 三、E1：历史地址方向与真实 GPC\n\n详细有符号差、不同加权、每 SM/轮次/地址及通信的源/目标主效应见 [GPC_ADDRESS_REANALYSIS.md](GPC_ADDRESS_REANALYSIS.md)。天然 34/22 偏好与旧冻结的 28/28 平衡组是两个对象，未互相改写。历史 region 的 0x33 类只用于原条带依赖读取，**没有赋给邮箱地址或本轮 KV 页**。\n\n![历史 GPC 方向](figures/01_historical_gpc_direction.png)',
'\n## 四、E2：相同 10 SM 的集中/分散\n\n下表是批量 GPU 完整核耗时变化；`SPREAD/PACK` 控制活跃配额和成员总覆盖。最后两列显示资源规模代价，不能把 10 SM 的内部优势称为全卡收益。全部单次 GPU/主机结果在派生表。',
table(['工作/CTA','SPREAD/PACK','PACK/E56','SPREAD/E56'],[[case,effect(find('E2',case,'SPREAD/PACK_family')),effect(find('E2',case,'PACK/E56')),effect(find('E2',case,'SPREAD/E56'))] for case in e2cases]),
'\n![等配额微基准](figures/02_equal_quota_micro.png)\n\nHOT2 每次读 2 MiB 唯一输入并复用 16 遍；逻辑读量不是实测显存流量。STREAM32/128 完整单遍；REG_FMA 是八条独立 FP32 FMA 链，不是 Tensor Core 代理。计算控制也可能受分布影响，因此本结果不能只凭读负载就定位 L2/互连瓶颈。',
'\n## 五、E3：原向量 GQA 主体上的迁移\n\n四种旧已见形状使用新输入与页表种子；offset 按块交替 0/65536。原冻结配置：SHORT DIRECT/W32/fused；LONG BLIND/W32/非融合；GQA8 BLIND/W32/非融合；RAGGED DIRECT/W16/非融合。没有为了 10 SM 缩小 CTA 网格。\n\n`_0` 为 Attention-only；`_1` 为变化 K/V 的固定长度末位更新 + Attention。后者四个新值槽循环变化，原始 KV 在方法之间恢复，非目标缓存内容检查不变。不是逐 token 增长/COW/完整模型推理。',
table(['形状/模式','SPREAD/PACK','E56/N19','PACK/N19','SPREAD/N19'],[[case,effect(find('E3',case,'SPREAD/PACK_family')),effect(find('E3',case,'E56/N19')),effect(find('E3',case,'PACK/N19')),effect(find('E3',case,'SPREAD/N19'))] for case in e3cases]),
'\n![GQA 迁移](figures/03_gqa_transfer.png)\n\n这些是完整算子 GPU 区间，但不包含 CPU 框架、输入 H2D/输出 D2H、缓存分配和初次建图。单请求主机 output-ready 同样保存。新旧数学顺序可相同的 DIRECT 非融合资格要求逐位相等；原 BLIND/最后到达融合允许已有非确定性，沿用原 `3e-4 + 3e-3×|ref|` 与相对 Frobenius ≤2e-3、第一头 FP64 检查，不放宽容差。',
'\n## 六、E4：全资源有用共置\n\n每份任务含 32 次变化值的 GQA 更新+Attention，以及固定数量的 FP16 输入/FP32 累积输出 cuBLAS GEMM（1024×2048×4096）。背景次数在任何 E4 放置性能出现前，按原生 pilot 冻结：LONG 为 7 次，RAGGED 为 9 次。所有策略处理相同输入序列、输出和工作量。两 stream 统一起点、末尾同时 join，没有中间 CPU 等待或无限背景压力。\n\nSHARED56 是普通未分区两 stream 并发；两串行参考保留。PACK/SPREAD/NEUTRAL 给前景 10 SM、背景确切互补 46 SM。“覆盖全资源”不代表每个 SM 每刻都满载。SHARED56_E56 是辅助主体控制：原生两 stream 上用 E56 主体，帮助单独看编译/入口差额；它不参与 14 个主安排的计数。\n\n前景/背景完成时间从同一个 job 起点计算；串行第二任务包含等待第一任务的时间，不是纯 kernel 服务时间。主机总时间等待两个输出都就绪。下表以 SHARED56 为参照，保留所有组，不把事后最优组当预先冻结算法。']
names=['SERIAL_GQA_FIRST','SERIAL_GEMM_FIRST','NEUTRAL10_46','PACK_G0','PACK_G1','PACK_G2','PACK_G3','PACK_G5','SPREAD_0','SPREAD_1','SPREAD_2','SPREAD_3','SPREAD_4','SHARED56_E56']
for cid in ['GQA4_LONG','BATCH4_RAGGED']:
 parts += ['\n### '+cid,table(['安排','整份 job 主机就绪','前景完成 GPU 区间','背景完成 GPU 区间'],[[name,effect(e4get(cid,name,'job_output_ready_us')),effect(e4get(cid,name,'foreground_completion_us')),effect(e4get(cid,name,'background_completion_us'))] for name in names]),'\n家族均值与强参照：',table(['比较','整份 job 主机就绪变化'],[[fam+'/'+ref,effect(find('E4',cid,fam+'/'+ref,'job_output_ready_us'))] for fam in ['PACK','SPREAD'] for ref in ['SHARED56','SERIAL_GQA_FIRST','SERIAL_GEMM_FIRST','NEUTRAL10_46','SHARED56_E56']])]
parts += ['\n![全资源共置](figures/04_full_resource_coexecution.png)',
'\n## 七、成本、噪声、审计与缺项\n\n主结果是准备完成后的固定混合 job，不是从进程启动算起的冷启动净账单。原始记录单列资源创建、Graph 构建、cuBLAS handle/workspace 和包含诊断的阶段准备时间。E2/E3 仅有直接测得的输入/Graph 设置成本，公共 CUDA/资源枚举与各重叠资源创建未完全分离，记为未独立计时，不补成 0。准备期可能含数值/位置诊断，不把整个研究准备当作生产最小必需成本。未作“无限请求可摊回本”的保证。\n\n原始 N19 与 E56 的同体全资源差异、A/A、首尾锚在 `derived/ANCHORS_AA.json` 和 `ALL_PHASES.json`。对照顺序是预定交错/正反轮换，不是 10/14 动作的完全 carryover 平衡。未对时钟回归校正，也未删长尾。',
f'\n目前账本 GPU-worker {seconds/60:.3f} / 180 分钟（含对应 worker 的 CPU 准备/资格，非纯 GPU busy）。实测遥测温度 {min(temperatures):.0f}–{max(temperatures):.0f}°C；100 W 上限和已有保护保持，82°C worker 停止阈值；未锁频、桌面进程仍存在。新下载、安装、SSH、付费、驱动/屏蔽/保护修改均为 0。墙时与完整最终校验见 `FINAL_AUDIT.json`。',
'\n已保存的工程事件：初始编译因默认旧 driver 头文件缺 Green 声明失败，改用本地已有匹配头；最初 CPU 重分析误把 28/28 平衡图当自然 34/22 图，断言失败后按历史报告定义修正。没有为此重跑 GPU 或重新拟合方向。E4 的准备计时在第一正式块前补齐并保留前版冻结文件。一次试图追加“每个正式 phase 的 Graph 审计”被运行状态断言阻止，没有改正在运行的正式程序；实际 Graph 审计另在独立诊断中完成。具体事件见 `ENGINEERING_NOTES.json`。',
'\n同体 GQA 页任务轨迹与 GEMM Graph 的独立诊断、有限 sanitizer 的实际范围、四次 CUPTI 活动结果以各自原日志和 `FINAL_AUDIT.json` 为准。诊断不进入主性能统计，不把一个代表的通过说成所有请求逐个检查。没有硬件内存/互连流量计数。未确认本地有可直接复用且范围匹配的专用 paged-decode 后端性能结果，不声称 N19 是所有专用库中的最优。',
'\n## 八、这轮能归因到哪里\n\n1. E1 是原构造下的 GPC 相关经验地址亲和；旧数据的后验硬件连接仍需承认缺少当时同时采集的 RM 表。当前 boot 早于两轮，UUID 和当前/历史 RM 表一致，但未独立排除中途驱动重载。\n2. E2/E3 的 PACK/SPREAD 干预控制同配额、同成员暴露和数学体，可以说明分布与有效执行代价关联。无 counter 时不能唯一定位共享 L2、互连、前端或频率机制。\n3. 若普通分散即解释收益，这属于普通资源放置/竞争控制，不能重新命名成新的地址 NUMA 算法。E4 才讨论全资源固定有用工作的表现，仍不是线上 SLA 或整模型 tokens/s。\n4. 不将本轮正数与旧 25 阶段百分比相加。也不因局部正结果扩搜、改 worker 数、挑最快 GPC 或在线训练选择器。\n5. 默认 N19/既有快核及先前 BASE54 不因本轮事后最优点自动替换。是否继续，应围绕这里仍未解释的对照差额，另立固定规则与跨日独立验证；本轮不保证论文新颖性或可发表。',
'\n## 九、交付与复算\n\n同目录有 `GPC_ADDRESS_REANALYSIS.md`、四组 PNG/PDF、最终审计、完整阶段与请求数据索引。主矩阵全部块级原值在 `derived/ALL_PHASES.json`；全策略、全部指标在 `ALL_POLICIES.json`，没有只打包正数。完整新 raw 留在当前运行目录，小包提供主比较原值、请求样本/数据、源码、冻结协议与复算入口。`recompute.py` 只做 CPU 复算，不启动 GPU、不执行历史方案中的命令。']
diag=read(RUN/'derived/DESCRIPTIVE_AUDIT.json')
parts.insert(1, '''## 先说本轮的直接结论

**实测到了 GPC 放置相关的机制差异，但本轮没有得到 GQA 拓扑/地址亲和调度的净加速。**

- 旧热依赖读取按 GPC 聚合后，`.cg` 的 class1−class0 为：GPC0 −1.522、GPC1 +1.662、GPC2 +1.658、GPC3 +1.800、GPC5 −1.506 周期/步；各 GPC 六块方向一致。`.ca` 在 GPC 聚合层也同方向，但这不等于原 `.ca` 整张残差图已稳定，更不证明两个物理 memory home。
- E2 批量视图的十二个等10SM条件中，分散家族平均均较集中快，下降1.92%–23.70%；热读取约17.79%–23.70%，流式读取约1.92%–7.99%，寄存器FMA约2.77%–5.92%。所有条件六块方向一致，但有明显锚点跳变，弱效应的因果强度需要保留意见。
- E3 同配额放置差异收缩到 −0.874%～+0.372%；三个批量比较区间虽不跨零，幅度仅约0.15%～0.27%，而全资源锚点存在更大漂移。不能包装成新的稳健算子收益。10SM分散相对原N19全资源慢94.0%～151.0%，原有并行能力损失远大于局部收益。E56/N19平均差额在−0.708%～+0.795%之间。
- E4 分散家族相对未分区并发，LONG整项任务耗时 **+23.111%**，RAGGED **+23.234%**。背景完成时间分别下降57.51%、60.34%，但前景完成时间增加约23%，尾部由前景决定。对两个串行参考也更慢。这是资源份额改变后的取舍，不能叫整体加速。分散相对集中，整项任务变化只有+0.028%、+0.002%。

直白地说：把同样十个工人分散到几个区域，在特定读数据测试里确实更有效；但把原来能用五十六个工人的GQA限制成十个，这笔损失没有补回来。让其余工人做GEMM会使GEMM更早结束，却没有让整份工作更早结束。新证据适合支持“存在GPC相关竞争、效果取决于负载和配额”的机制边界，尚不支持新的NUMA地址调度加速算法。''')
detail=['\n## 十、噪声敏感性、绝对时间与成本补表',
'### 噪声不能藏在附件中\n\nE2 的 STREAM128_CG_40，首个 A/A 的块间几何平均变化 −11.947%，首尾变化 −10.968%；HOT2_CG_40 某一块首尾变化达到 −30.943%。E3 的 BATCH4_RAGGED 更新模式，首尾平均变化 +6.685%，LONG 更新模式尾部 A/A 平均 −5.287%。E4 首尾平均变化约 +1.42%～+2.16%。这些变化均保留，没有剔除样本、时钟回归或改写原比较。短锚点的采样量比主phase小，不能精确定位状态变化原因。交错顺序和成员覆盖减轻了部分混淆，但不是完整carryover平衡。尤其不能因六块bootstrap区间很窄，就忽略系统性顺序和状态误差。',
'下面改用四个原始锚点作参照，只检查E4结论是否依赖单个参考时刻，不对主结果作漂移校正：',
table(['前景','分散/头锚','分散/头AA','分散/尾锚','分散/尾AA'],[[cid]+[f"{next(x['time_change_percent'] for x in diag['alternate_anchor_sensitivity'] if x['stage']=='E4' and x['case']==cid and x['family']=='SPREAD' and x['reference_role']==ref):+.3f}%" for ref in ['ANCHOR_HEAD','AA_HEAD','ANCHOR_TAIL','AA_TAIL']] for cid in ['GQA4_LONG','BATCH4_RAGGED']]),
'换参照后整项任务仍慢约21.5%～24.5%，本轮“未回本”的结论不依赖只取头锚或尾锚。所有阶段的同类敏感性和块级比值在 `derived/DESCRIPTIVE_AUDIT.json`；不用上述检查把微小正值升级为稳健收益。',
'### 完整混合任务的绝对时间\n\n以下为六块几何平均，单位ms；前后台均从统一job起点计。全部策略均列出，SHARED56本身也给出原值：',
table(['前景','安排','整项就绪ms','前景完成ms','背景完成ms'],[[x['case'],x['policy']]+[f"{x['geometric_mean_ms'][k]:.4f}" for k in ['job_output_ready_us','foreground_completion_us','background_completion_us']] for x in diag['e4_absolute']]),
'### 一次性准备与诊断范围\n\n以下成本跨两种前景的12个主phase汇总，单位ms；Graph构建为四个输入槽，背景handle含workspace。包括位置探测的研究准备不是生产最低成本。SHARED56的resource为0表示本phase不创建显式分区，不表示进程初始化免费。',
table(['安排','成本项','最小ms','中位ms','最大ms'],[[x['policy'],x['cost'],f"{x['minimum']:.3f}",f"{x['median']:.3f}",f"{x['maximum']:.3f}"] for x in diag['setup_costs'] if x['stage']=='E4' and x['policy'] in ['SHARED56','PACK_G0','SPREAD_0']]),
'全部放置的准备成本均保留。本轮热态job已经更慢，因此不能用摊销初始化成本把结果说成正收益。E2/E3缺少独立资源创建计时，列为NA及明确原因，不能据此给出冷启动净成本。',
'独立GQA轨迹480次通过；GEMM的72份独立Graph均为 `turing_s1688gemm_fp16_256x128_ldg8_stages_32x1_nn`，grid=8×8×2、block=256、动态shared=16384字节。四份CUPTI时间线都有真实前后台重叠，但profile开销较大，不能替代主计时。memcheck和synccheck各覆盖24个微基准launch及8个分页尾部GQA调用，均报告0错误；这不是对所有正式请求逐一做sanitizer。',
'本地Python环境的 flashinfer、vllm、flash_attn、xformers 模块查找均不存在；旧18/19阶段报告也仅给出SDPA/BMM等对照，未确认可直接运行的专用paged-decode后端。因此本项记NA，本轮没有联网安装或移植；该盘点不代表穷尽所有可能独立二进制。',
'### 尚未解决与下一步边界\n\n现有证据没有分开物理memory home、具体共享资源瓶颈、频率/前端效应；没有跨日/跨卡复验，也没有真实模型动态KV生命周期和专用decode强对照。固定10/46配额的结果不能代表所有配额都失败，但也不授权据此无边界搜索新配额。若后续另立任务，应先选真实有用的混合工作与预先固定的份额，要求完整job击败未分区及串行，再讨论放置增量；目前不替换默认快核、不扩大Softmax/地址mask/在线选择器搜索。']
parts.extend(detail)
(R/'T10_GPC_CONTENTION_GQA_REPORT.md').write_text('\n\n'.join(parts)+'\n')
hist=read(RUN/'derived/E1/SUMMARY.json');comm=read(RUN/'derived/E1/COMMUNICATION_COMPARISONS.json')
hp=['# GPC 与历史地址/通信数据的交叉重分析','六个第15阶段进程，每进程两轮；保留开发0/1、原确认2/3、后续独立确认4/5。以下连接使用第22阶段实读映射；本次RM完全相同，同一UUID且当前boot早于两个阶段，但历史第15阶段没有同时记录RM，不能独立排除中间驱动重载。没有新GPU矩阵，也没有新选mask/配对。','## 有符号地址差','原数据是2MiB、4KiB交错条带、128B间距的热依赖读取，先256步再计1024步。`class1 − class0` 为正表示类0较快；两时钟分列，不称裸L2延迟。自然组34/22分别是GPC{1,2,3}/{0,5}，不同于旧冻结28/28平衡图。']
for unit in ['cycles','ns']:
 hp+=['### '+unit,table(['cache','GPC','class1−class0','95%块区间','六块原值'],[[x['cache'],x['gpc'],f"{x['class1_minus_class0']:+.6f}",str([round(v,6) for v in x['difference_ci95']]),', '.join(f'{v:+.4f}' for v in x['block_differences'])] for x in hist['gpc_signed'] if x['unit']==unit])]
hp+=['## 34/22 不等规模的两种加权',table(['cache','单位','权重','自然组','差值均值','六块差值'],[[x['cache'],x['unit'],x['weighting'],x['historical_group'],f"{x['mean']:+.6f}",', '.join(f'{v:+.4f}' for v in x['block_signed_difference'])] for x in hist['group_weighting']]),'## 邮箱往返：保留发送者与接收者主效应','邮箱记录保留实际 flags VA、slot偏移0/17/257页、请求/应答/payload地址。没有把条带region的0x33赋给邮箱。同行发送者、同地址、同轮次先比较接收者类别，再对SM/轮次和进程等权。same-SM同CTA对角不进入跨SM类别比较。下表使用源/目标两向log残差后的类别差；原始类别比、发送者/接收者主效应也完整保存。这里的百分比是残差比的表达，不能当作裸连线距离或应用速度。']
hp += [table(['载荷模式','slot','单位','类别/跨偏好组','残差变化95%'],[[x['mode'],x['slot'],x['unit'],x['category'],effect(x)] for x in comm if x['field']=='row_column_residual_difference' and x['unit']=='cycles']), '## 可复算数据','`derived/E1/` 内包含逐SM/region/round原值与两向残差、逐GPC格、逐SM类间有符号差、逐发送者通信类别、源/目标主效应及完整配对行。原始records.bin来源和哈希在 SOURCE_PROVENANCE.json。未创建不存在的逐轮数据；此次确实从保存的逐轮记录读取。缺少物理地址、home、远端流量与同时RM记录的边界不变。']
(R/'GPC_ADDRESS_REANALYSIS.md').write_text('\n\n'.join(hp)+'\n')
print('REPORTS_WRITTEN')
