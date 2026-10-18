from pathlib import Path
import json,numpy as np,hashlib
from compile_topology_schedule import compile_schedule
R=Path(__file__).resolve().parents[1];d=R/'derived';r=json.loads((d/'RESULTS.json').read_text());v3=json.loads((R/'freeze/MAPPING_V3.json').read_text());run=next((R/'runs').iterdir());p=r['address_preference']
t=np.load(d/'address_conditioned_tensor.npz')['cycles'];cost=t[:2].mean(axis=(0,1));model=dict(type='EMPIRICAL_ADDRESS_CONDITIONED_COST_MODEL',device_uuid=json.loads((R/'BEGIN_EXECUTION.json').read_text())['uuid'],architecture='sm_75',sm_roster=r['roster'],producer_sms=r['roster'][::2],consumer_sms=r['roster'][1::2],mailbox_base_pages=[0,17,257],mailbox_stride_bytes=4096,allocation_scope='Relative offsets inside the private2MiB flags allocation used by this protocol. New processes are new allocations, not proof of different physical pages.',development_cost_cycles=cost.tolist(),calibration_sources=['tensor_dev_0','tensor_dev_1'],class0_preferred_sms=p['class0_preferred_sms'],class1_preferred_sms=p['class1_preferred_sms'],physical_topology_known=False)
(d/'TOPOLOGY_MODEL.json').write_text(json.dumps(model,indent=2)+'\n')
for page in [0,17,257]:
 for objective,name in [('minimax','ADDRESS_MAX'),('sum','ADDRESS_SUM')]:
  actual=compile_schedule(model,page,objective);expected=next(m for m in v3['maps'] if m['slot_page']==page and m['name']==name);assert actual['pairs']==expected['pairs'];(d/f'SCHEDULE_page{page}_{objective}.json').write_text(json.dumps(actual,indent=2)+'\n')
def summary(version,contrast):return next(x for x in r[version] if x['contrast']==contrast and 'steps' not in x)
def gain(v,c):return summary(v,c)['gain_percent']
s=['# T10 SM 通信拓扑与地址感知调度：最终报告','',
'本轮完成了逐SM通信测量、地址亲和测量及三版真实执行的配对调度原型。**现在有可复验、可直接输入调度器的实测代价图；仍没有确认芯片的物理连线、GPC坐标或两个物理NUMA节点。**',
'',f'运行目录：`{run}`。本轮新增GPU-worker **{r["resources"]["gpu_worker_seconds"]/60:.4f}/15分钟**，独立于上一轮已关闭的330分钟预算；全部GPU工作结束，无继续运行队列。100W上限保持，采样温度62–67°C。',
'','## 1. 现在能确定什么','',
'1. **SM之间的通信代价不是一个固定常数。** 测了56×56有向关系，包含只通知与64B交接、3个缓冲位置、每进程2轮，共6个进程。相同地址集合的64B交接周期残差，开发与最后两次独立确认相关约0.981。这里先扣除了源SM和目标SM各自的整体快慢，避免把一个SM普遍较快误当成某一对特别近。',
'2. **这张图必须带地址条件。** 用前两个缓冲位置的配对关系去预测第三个位置，64B残差相关仅0.078。前两个位置与第三个位置不能混称一张固定SM距离图。新进程复现稳定与跨地址迁移稳定是两个命题。',
'3. **SM—地址亲和有清楚的两类偏好。** 沿用旧的`parity(region &0x33)`分类，34个SM偏好类0，22个SM偏好类1，全部56个SM的偏好方向在6个进程中一致。自然偏好组不是为了平衡负载而强制分出的28/28组，也不是物理NUMA节点。',
f'4. **已经实现一个小幅有效的原型。** 最终地址感知、优先降低最慢交接对的调度，在6个新的进程中，通信事件区间耗时相对固定配对减少{gain("v3","ADDRESS_MAX/IDENTITY"):.2f}%，相对随机配对减少{gain("v3","ADDRESS_MAX/RANDOM"):.2f}%，相对不看地址的周期最慢对调度再减少{gain("v3","ADDRESS_MAX/GLOBAL_CYCLE_MAX"):.2f}%。这是合成通信内核内的效果，不是渲染、GEMM或模型端到端提速。',
'','![完整SM通信矩阵](figures/01_sm_pair_topology.png)','',
'## 2. 实测拓扑的具体样子','',
'应表示成`C(source SM, destination SM, mailbox address, payload, concurrency)`，而不是只写`distance(SMi,SMj)`。每个方向的往返时间包含全局内存访问、轮询、release/acquire顺序和线程执行；不能除以2就叫单向网络延迟，也不能从矩阵唯一反推出物理连线。',
'', '固定旧地址分类：`region`是自有2MiB数据中按4KiB交错的区域编号，64个区域各跨8个4KiB片段。类号是`popcount(region &0x33)%2`。依赖链访问采用128B间距、每区域256个节点、先走256步再测1024步；`.cg`与`.ca`分开。它是指定缓存策略下的热依赖读取，缺少硬件计数器，不能承诺每步都是某一级cache命中。',
'','| 实测偏好 | 实际SM编号 |','|---|---|',
'| 类0较快，34个 | '+', '.join(map(str,p['class0_preferred_sms']))+' |',
'| 类1较快，22个 | '+', '.join(map(str,p['class1_preferred_sms']))+' |',
'','当前编号下可简写为：`SM%10∈{4,5,6,7}`偏好类1，其余已观察SM偏好类0。这只是本次数据的描述性编码，**不能据此说每10个SM就是一个GPC**。六个进程中单SM类间差通常约1.4–1.9周期，相比每步约230周期是小效应。该规则只对这里的地址构造和缓存策略有证据。',
'','![地址亲和](figures/03_address_affinity.png)','',
'通信关系还包含地址亲和以外的配对结构。开发期选出的8条“双方都把对方排入相对较快前三”的边，全部在最后两个确认进程中保持负残差。下表是扣除行列主效应后的对称残差，不是绝对距离、物理邻接或应用节省百分比。',
'','| SM对 | 新确认相对残差 |','|---|---|']
for e in r['edges']:s.append(f'| {e["sm_a"]} ↔ {e["sm_b"]} | {e["new_confirmation_mean_percent"]:+.2f}% |')
s += ['', '![配对关系与地址迁移](figures/02_pattern_replication.png)','',
'`.ca`地址残差没有表现出同等稳定性：最后两次确认与开发的相关约0.229；`.cg`约0.947。不会把一种缓存策略下的规律推广到所有访问方式。循环/寻址开销保留在每步计时内，没有把结果改称纯L2延迟。',
'','## 3. 已实现的优化及全部迭代结果','',
'运行器使用公开cooperative launch；48KiB动态shared memory与占用率API资格检查保证每SM至多一个CTA，56个CTA覆盖全部56SM。每次启动都记录实际SM起止编号，核对无缺失、重复和已检测到的迁移。隔离测量时，其余SM在初始grid同步后退出，不在计时期间持续轮询。通信的开始与结束在同一源SM计时，同时保存clock64和globaltimer，不跨SM相减时钟。',
'','部署原型把排序后的偶数位置SM作为28个生产者、奇数位置SM作为28个消费者。各生产者的信箱地址和工作量固定，只改变消费者配对。所有策略执行相同64B内容及校验、28对同时推进、每对128或512次正式往返，另有每核16次相同预热。主指标是CUDA事件包围的完整通信提交区间，包含协作初始化、表读取、内部预热和可能的启动间隙。每条件3次预热启动原始记录保留但不计入估计。',
'','| 阶段 | 实现 | 对固定配对耗时减少 | 对随机配对耗时减少 | 新独立部署进程 |','|---|---|---:|---:|---:|',
f'| V1 | 最小化孤立测量的平均纳秒 | {gain("v1","MIN/IDENTITY"):+.3f}% | {gain("v1","MIN/RANDOM"):+.3f}% | 4 |',
f'| V2 | 周期代价，优先最小化最慢一对 | {gain("v2","CYCLE_MAX/IDENTITY"):+.3f}% | {gain("v2","CYCLE_MAX/RANDOM"):+.3f}% | 6 |',
f'| V3 | 每个生产者使用实际信箱位置，按地址分别最小化最慢一对 | {gain("v3","ADDRESS_MAX/IDENTITY"):+.3f}% | {gain("v3","ADDRESS_MAX/RANDOM"):+.3f}% | 6 |',
'','V2、V3都是在上一版结果出来后明确新增的适应性阶段，各自冻结方案后再使用新进程测试。没有把整个三版过程说成一次预登记确认。V1负结果保留，V3为本轮预定最后一版，没有继续选一个更好看的方法。',
'','V3对每个固定生产者测试所有28个消费者，信箱恰为部署时`base+(slot_page+producer_index)*4096`，3个slot_page为0、17、257。2个开发进程仅用于生成映射，随后2个新进程确认代价矩阵，再用6个新进程检验并发效果。每个地址条件对应一张28×28代价表。其周期残差开发/确认相关分别约0.968、0.964、0.980。',
'','算法已实现：Hungarian精确最小总和；二分阈值与完全匹配求最小最大值，再以最小总和打破并列。小规模问题用穷举独立核对。最终CPU编译入口是`src/compile_topology_schedule.py`，只接受已校准的地址位置；不把未知位置强行套进旧映射。',
'','![最终优化](figures/08_final_address_aware_optimization.png)','',
'| V3比较 | 六进程汇总耗时减少 | 各进程范围 | 汇总为正的进程 |','|---|---:|---:|---:|']
for x in r['v3']:
 if 'steps' not in x:s.append(f'| {x["contrast"]} | {x["gain_percent"]:+.3f}% | {x["block_min_gain_percent"]:+.3f}%～{x["block_max_gain_percent"]:+.3f}% | {x["positive_blocks"]}/{x["processes"]} |')
s += ['', '六个进程汇总都为正，不表示所有单条件都为正。例如V3相对V2在128往返、page0条件汇总约−0.040%，只有3/6进程为正；该条件相对随机也有一个负进程。完整6条件及逐进程值保留在RESULTS.json，不删除波动或改变汇总权重。',
'','GPU内部最长源线程循环的诊断计时也支持同一方向：V3相对固定配对约+2.449%，相对随机约+1.107%，相对V2约+0.479%。这降低了“收益全部来自主机提交间隙”的解释空间；最长单线程循环仍不是精确的整个内核活动跨度，不冒充CUPTI内核时间线。',
'','## 4. 哪些结论仍不能写','',
'- **没有物理拓扑证明。** 没有物理地址、GPC位置、L2 home或互连流量计数；SM编号不是几何坐标。信箱换位置导致配对模式改变，尤其不支持一张与地址无关的SM近远表。',
'- **不是应用部署收益。** 校准、CPU求解、映射H2D、完整输入输出及真实算子均在本轮主计时之外。每SM只保留一个CTA、占用48KiB shared memory是测量/原型控制，迁移到成熟GEMM可能损失占用率和数学吞吐。',
'- **不是普遍稳定百分比。** 仅此T10、固定100W上限、这组地址与载荷、这批进程。没有锁频；桌面GPU客户仍在；绝对纳秒受运行状态影响。六进程描述性汇总不等于跨机器、跨日或跨驱动保证，也未把几十万记录当作独立样本计算显著性。',
'- **没有证明低并发矩阵准确预测拥塞。** 最小最大值来自孤立配对，只是并发性能的启发式代理；原型结果必须实际检验，不能从代价表推导全资源必然提速。',
'- **自然34/22组与冻结28/28组不同。** 早期SVD诊断为平衡展示固定了28/28；自然偏好按固定0x33类间差符号得到34/22。两套对象和各自定义都保留，不用自然组结果改写旧冻结规则的估计。',
'','## 5. 质量、失败与资源记录','',
f'CPU逐条复核了 **{r["audit_summary"]["placement_launches_checked"]:,}次启动的实际SM覆盖**、**{r["audit_summary"]["records_checked"]:,}条记录的起止位置/错误状态/完成计数或链终点**。GPU程序对每次64B消费检查16个整数的和；错误标志全部为0。原始payload本身未逐轮导出，CPU复核的是保存的设备校验状态和确定性终点，并非重新执行GPU。',
'','完整包保留memcheck/synccheck零错误日志、源码、SASS、固定计划与映射、二进制、全部raw及1Hz只读NVML。首次调用工具包内不完整的sanitizer启动器因缺少注入库退出，未开始GPU检查；改用已有完整vendor包后通过。磁盘保护曾在deploy_v2_4启动前停止，清理423MB旧临时QA解压副本后用新输出名接续；原始实验和最终归档不删。',
'','源/二进制审计保持冻结对象不变。通用worker的`manifest.binaries`字段一直是原build参考值；V2/V3实际二进制按命令路径及各阶段冻结哈希解析，在`AUDIT.json/actual_binary_bindings`逐项给出，不能误用旧字段声称后两版用了旧cubin。',
'','新进程确实重新分配了缓冲区，但虚拟地址可以复用，物理页独立性未知。所有实际VA、SM roster和监测样本保留。没有下载、安装、管理员设置更改，资源租赁0元（用户此前说明）；电费未测。',
'','## 6. 下一步实现落点','',
'本轮给出的可用设计原则是：**把生产者、消费者和数据位置一起安排，并优化最长依赖链的完成时间。** 接入真实算子时，优先让生产者直接在目标布局生成partial/队列槽，复用已资格的长期资源与映射；不能额外搬运一遍数据再把搬运成本藏在计时外。应与同等融合、同等资源占用的固定配对和成熟原生实现比较完整output-ready时间。',
'','尚需解决的是生产执行器的占用率成本、校准/分配变化后的失效检测，以及满载下的并发竞争。当前结果支持继续围绕地址感知的算子内交接优化，不支持宣称已实现通用GPU NUMA加速。',
'','## 7. 文件与复算','',
'- `derived/pair_matrix.csv`：逐进程、逐信箱位置、逐方向的56×56原始量纲均值，对角同CTA控制单独标注。',
'- `derived/address_matrix.csv`：56×64地址矩阵，`.cg/.ca`与纳秒/周期分列。',
'- `derived/address_conditioned_tensor.csv`：V3实际部署地址对应的28×28代价表。',
'- `derived/TOPOLOGY_MODEL.json`与`SCHEDULE_page*_minimax.json`：模型与可执行配对。',
'- `freeze/PROTOCOL*.json`：阶段冻结合同；`runs/*/raw`：全部原始值。',
'- `README_REPRODUCE.md`与`src/recompute.py`：不访问GPU的独立解压复算。',
'','官方语义依据：[NVIDIA PTX SMID](https://docs.nvidia.com/cuda/parallel-thread-execution/index.html#special-registers-smid)说明SM编号不保证连续、可能随抢占重调度改变；[globaltimer](https://docs.nvidia.com/cuda/parallel-thread-execution/index.html#special-registers-globaltimer)是目标相关计时寄存器；[CUDA cooperative grid synchronization](https://docs.nvidia.com/cuda/archive/12.3.2/cuda-c-programming-guide/index.html#grid-synchronization-cg)提供协作驻留/同步的约束。本轮检查实际覆盖及起止SM，固定编译sm75，同时保留两种时钟；这些API语义没有提供物理连线位置。']
(R/'reports/T10_SM_TOPOLOGY_AND_OPTIMIZATION_REPORT.md').write_text('\n'.join(s)+'\n')
print('Report, topology model and six reusable schedules generated; all schedules exactly match executed frozen mappings.')
