from common import *
import numpy as np,collections
def find(stage,comparison,case='ALL',metric='gpu',**kw):
 return next(x for x in read(ROOT/f'derived/{stage}.json')['results'] if x['comparison']==comparison and x['case']==case and x['metric']==metric and all(x[k]==v for k,v in kw.items()))
def number(x,ci='ci95_pct'):return f"{x['gain_pct']:+.3f}% [{x[ci][0]:+.3f}, {x[ci][1]:+.3f}]"
def table(stage,comparisons,cases,**kw):
 lines=['| 条件 | '+' | '.join(comparisons)+' |','|---|'+'---|'*len(comparisons)]
 for case in cases:lines.append('| '+case+' | '+' | '.join(number(find(stage,c,case,**kw)) for c in comparisons)+' |')
 return '\n'.join(lines)
def main():
 audit=read(ROOT/'derived/AUDIT.json');choice=read(ROOT/'freeze/MAILBOX_CHOICE.json')['page'];cases=['ALL','VOCAB_32768','VOCAB_65536','VOCAB_131072','VOCAB_262144'];attn=['ALL']+[c['id'] for c in read(ROOT/'freeze/PROTOCOL.json')['cases']]
 central={key:find('const_confirm',key,scope='ready',address='ALL') for key in ['MINIMAX/IDENTITY','MINIMAX/RANDOM_POOL','MINIMAX/NATIVE','MINIMAX/WRONG_ADDRESS']};common=find('soft_common','MINIMAX/IDENTITY');batch=find('soft_batch','MINIMAX/IDENTITY');fresh=find('const_confirm','MINIMAX/IDENTITY',scope='fresh',address='ALL')
 target={c:find('const_confirm',c,'VOCAB_131072',scope='ready',address=choice) for c in ['MINIMAX/NATIVE','MINIMAX/IDENTITY','MINIMAX/RANDOM_POOL','MINIMAX/WRONG_ADDRESS']}
 target_batch=next(x for x in read(ROOT/'derived/soft_batch.json')['by_address_results'] if x['address']==choice and x['case']=='VOCAB_131072' and x['comparison']=='MINIMAX/IDENTITY')
 gates=[]
 for c in cases[1:]:
  primary=[find('const_confirm',p,c,scope='ready',address=choice) for p in ['MINIMAX/NATIVE','MINIMAX/IDENTITY','MINIMAX/RANDOM_POOL']]
  robust=[find('const_confirm',p,c,scope='fresh',address=choice) for p in ['MINIMAX/NATIVE','MINIMAX/IDENTITY','MINIMAX/RANDOM_POOL']]
  address=[find('const_confirm','MINIMAX/WRONG_ADDRESS',c,scope=s,address=choice) for s in ['ready','fresh']]
  gates.append(dict(case=c,mailbox_page=choice,primary_all_lower_ci9875_positive=all(x['ci9875_pct'][0]>0 for x in primary),fresh_all_lower_ci9875_positive=all(x['ci9875_pct'][0]>0 for x in robust),strict_address_specific_lower_ci9875_positive=all(x['ci9875_pct'][0]>0 for x in address),primary=primary,fresh=robust,address_specific=address))
 write(ROOT/'derived/DEPLOYMENT_GATE.json',dict(gates=gates,scope='Descriptive validation gate; no separately tested routing policy. API remains explicit experimental policy, NATIVE default. Physical NUMA/SM mask geometry not established.'))
 offline=sum(read(RUN/f'soft_tensor_{i}/manifest.json')['worker_seconds'] for i in [0,1]);fit=read(ROOT/'freeze/SOFTMAX_MAPS.json')['fit_ms'];timings=[]
 for p in RUN.glob('api_*/api.json'):timings.extend(read(p))
 setup=collections.defaultdict(list)
 for x in timings:setup[x['V'],x['policy']].append(x['setup_ms'])
 setup_lines=['| V | NATIVE plan ms | MINIMAX plan ms | IDENTITY plan ms |','|---|---:|---:|---:|']
 for V in [32768,65536,131072,262144]:setup_lines.append(f"| {V} | {np.median(setup[V,'NATIVE']):.3f} | {np.median(setup[V,'MINIMAX']):.3f} | {np.median(setup[V,'IDENTITY']):.3f} |")
 costs=read(ROOT/'derived/COSTS.json');cost_lines=['| V | 参照 | 配对平均节省 µs | 复用离线模型估算回本请求 | 本次重校准也计入的估算回本请求 |','|---|---|---:|---:|---:|']
 for x in costs['rows']:cost_lines.append(f"| {x['V']} | {x['baseline']} | {x['paired_mean_saving_us']:+.4f} | {x['offline_model_reused_break_even_requests'] if x['offline_model_reused_break_even_requests'] is not None else '无有限回本点'} | {x['recalibrate_this_device_break_even_requests'] if x['recalibrate_this_device_break_even_requests'] is not None else '无有限回本点'} |")
 text=f'''# T10：冻结快核后的地址亲和与 SM 归并调度

本轮运行 `{RUN.name}`，本地日期 2026-10-18。所有百分比都是 `100×(1−T_method/T_control)`：正数表示完整 GPU 时间减少；默认方括号为 95% 进程 bootstrap 区间。大幅普通融合收益与很小的 SM 配对增量分开报告。

## 最关键的结果

原 Attention 快核已按 SHA256 原样冻结并保留。一次领取整组页面的地址调度相对该快核汇总 **{number(find('claim_confirm','MATCH/FAST'))}**，相对同开销盲调度 **{number(find('claim_confirm','MATCH/BLIND'))}**。它没有实现用户要求的收益，未替换原实现。

得到一个**受限的单核正结果**：131072 词表、只按训练微测预选的邮箱页 {choice}、输入已经预热且本次不重写。只改变同一常量参数 kernel 的配对，MINIMAX/IDENTITY 为 **{number(target['MINIMAX/IDENTITY'],'ci9875_pct')}**，相对 12 套随机配对为 **{number(target['MINIMAX/RANDOM_POOL'],'ci9875_pct')}**，相对错误地址配对为 **{number(target['MINIMAX/WRONG_ADDRESS'],'ci9875_pct')}**；这三项各 6/6 新进程为正，区间已按四个词表作 98.75% 修正。

但该正结果**没有稳定延续到每次重写 logits 的条件或连续批量节奏**。因此本轮结论是“找到了条件性的 SM/地址配对增量”，不是“已经获得可通用部署的 NUMA 净加速”。下文保留了缩小、消失和反向的结果，默认接口仍不启用该映射。

转到真实计算的 FP32 单 token 词表 Softmax 后，最终常量参数版只改变 SM 配对：跨四个词表、三个邮箱位置等权，MINIMAX/IDENTITY 为 **{number(central['MINIMAX/IDENTITY'])}**，MINIMAX/12 套随机配对几何平均为 **{number(central['MINIMAX/RANDOM_POOL'])}**。重写 logits 的完整“copy→Softmax”条件下，MINIMAX/IDENTITY 为 **{number(fresh)}**。原二进制与同一张映射表地址的独立控制为 **{number(common)}**；32 次完整算子批量计时控制为 **{number(batch)}**。

这几组控制分别检验配对、映射表本身的存放位置、输入写入后的缓存状态及计时粒度。不能用其中一张正表覆盖另一张负表。最终逐形状判定见 `derived/DEPLOYMENT_GATE.json`；该 gate 是测试后明确列出的使用限制，不是又一个独立验证过的自动路由策略。API 默认 NATIVE，MINIMAX 必须显式指定。

这里的工作是合成但实际执行的 LLM 尺寸部件；没有运行模型权重、完整生成、top-k/top-p 采样或输出投影。小词表可能输给普通方案；大词表相对普通两阶段实现的收益主要来自单 kernel 归并融合，不能全部算作 NUMA。

## 1. 保持什么不变，究竟改变什么

Attention 保持上一轮向量读取、共享 KV、写入融合及 W/归并配置；对照的 `build/baseline/vector.so`、`vector_append.so` 与上一轮逐字节相同。新候选提前把页按历史地址类分成完整 worker job，每 CTA 最多两次队列领取，不再逐页做原子操作。保留 CA/CG 两种加载、盲选、匹配、反向、打乱及静态控制；仅在两个开发进程选择 CA/CG，然后六新进程复验。资格 trace 显示匹配策略约九成任务被送到其假设偏好的 SM 类，而盲调度约一半，所以本轮失败不能简单归因于“没有真的改变任务位置”。这也不证明原地址规则适用于快核的实际访问路径。

Softmax 的每个 SM 固定读取同一组 logits、做同样的 max/sum/exp 工作；56 个 SM 分成 28 个偶数 ID 生产者和 28 个奇数 ID 消费者。生产者的 8 字节 `(max,sum)` 固定写到自己的邮箱。只改变哪一个消费者读取哪一个生产者，随后最后一个消费者完成全局归并并通知所有 SM 写出完整概率向量。没有在真实算子里添加反复 ping-pong 来放大收益。

这里“固定各 SM 的工作”不等于所有 SM 的有效元素数完全相等：这些词表尺寸不能整除 56×128，尾部有效元素分布保持固定。配对改变仍可能改变计算尾部与通信等待的重叠；最后归并者也未固定。因此通过的对照支持**配对安排的净效果**，尚不能将全部增量唯一归因于物理链路延迟。下一轮需在均衡每 SM 有效工作量、固定最终归并者之后再验证通信关键路径。

所有配对执行同一个编译内核、同样的网格、线程数、48 KiB 动态共享内存保留、轮询、计数和输出；配对改变会影响到达顺序及最后归并者，这是调度效果的一部分。初始化、全网格同步、等待、收尾与计数复位全部在计时区间。普通 NATIVE 是同精度的全 GPU 两阶段 Softmax；另保留 torch.softmax 和同一融合 kernel 的固定/随机配对。没有宣称超过所有现有优化 Softmax 或采样实现。

固定 56 个 cooperative CTA，每 CTA 128 线程，运行时 occupancy 检查要求每 SM 最多一个 CTA；诊断 trace 要求实际 SM 0–55 各一次、起止不变。48 KiB 动态空间加少量静态空间需要显式 opt-in，初版遗漏造成的 launch 失败已保存，修复后重新资格检查。这里的资源保留和同步成本均被计入；不能把它当成免费绑核。

最终 `softmax_const.cu` 将 56 个映射整数作为 kernel 参数按值传入。SASS 包含从同一参数偏移 `c[0x0][R+0x160]` 的 LDC，所有配对使用同一个参数位置；不再因策略不同而换全局映射表地址，热态不建表、不上传、不分配显存。编译日志保留寄存器及 spill 信息。原全局表版和独立“同一表地址、只换内容”控制仍完整保留。

## 2. 拓扑证据是什么

重测实际使用的 8 字节消息，而非沿用 64 字节结果。对 28×28 有向生产者/消费者组合，在邮箱基址相对页 0、17、257 分别测量；每个固定生产者的邮箱位于 `2MiB-aligned base+(page+producer_index)*4096`。四个进程各 4704 个孤立 pair launch，两个开发、两个独立校验；每次含 16 次预热和 128 次有效往返，内容、序号、SM 和超时全部验证。计时由同一生产者的 clock64 完成，不相减不同 SM 的时钟。

训练周期矩阵作最小最大成本完美匹配，并用总成本打破平局；还保留最小和、最大和、固定及随机映射。模型在任何 Softmax 开发测量之前冻结。邮箱位置 {choice} 是常量参数实验前只根据训练矩阵最小预测最大 RTT 选出的，三个位置的全部数据仍保留。

![8-byte address-conditioned topology](figures/topology.png)

`derived/softmax_topology.json` 给出独立校验矩阵和去行列主效应后的相关性；这次三个地址位置的残差相关约 0.591、0.171、0.430，弱于以前的部分 64 字节结果。图表示特定地址、消息和加载条件下的经验往返代价，**不表示芯片平面坐标、物理 NUMA 节点、单向跳数或被屏蔽 SM 的几何形状**。当前只校准 even→odd 部分；旧完整 56×56 结果在上轮 `sm-topology-t10`，不能冒充本轮全矩阵。

[NVIDIA PTX 对 SMID 的定义](https://docs.nvidia.com/cuda/parallel-thread-execution/index.html#special-registers-smid)不保证 ID 连续或在调度变化中恒定，因此本机实测 roster 是必要约束，编号大小不是距离。[CUDA Cooperative Groups 文档](https://docs.nvidia.com/cuda/cuda-programming-guide/04-special-topics/cooperative-groups.html)提供公开的协作启动和网格同步机制；本轮没有使用未公开 SM 掩码接口。

## 3. Attention：失败也完整保留

{table('claim_confirm',['MATCH/FAST','MATCH/BLIND','MATCH/INVERT','MATCH/SHUFFLE'],attn)}

GQA8 的较大退化显示减少原子数并不足以抵消整组领取带来的负载与资源代价；本轮没有用硬件计数器隔离出唯一原因。trace 约九成地址匹配是实现证据，不是快核成功证据。

## 4. Softmax：全局映射表版及更严格控制

第一轮六进程、所有地址等权：

{table('soft_confirm',['MINIMAX/FAST','MINIMAX/IDENTITY','MINIMAX/RANDOM','MINIMAX/WRONG_ADDRESS'],cases)}

每地址 12 套随机配对的独立六进程面板：

{table('soft_panel',['MINIMAX/IDENTITY','MINIMAX/RANDOM_POOL','MINIMAX/WRONG_ADDRESS'],cases)}

孤立通信成本对完整 kernel 时间的预测仍弱：在这 12 个词表×地址条件中，随机/固定/学习配对的训练平均 RTT 与实测完整时间相关性约为 −0.199 到 +0.331，中位数约 +0.158，详见 `derived/soft_cost_transfer.json`。因此，即使冻结配对有正增量，也不能宣称孤立 pair 成本已经解释或预测了整个归并图。最后归并者会随到达顺序变化，P→C、原子 fan-in 和最终通知的贡献尚未分别隔离。

随机面板均值也不等于“经独立开发调优后的最快随机配对”。本轮没有把确认集里的随机赢家当免费基线，同时也不主张学习映射优于预算相当的随机搜索；这是形成更强论文主张时仍需补的对照。

同一原二进制、相同映射表 VA 的独立六进程：

{table('soft_common',['MINIMAX/IDENTITY','MINIMAX/RANDOM','MINIMAX/WRONG_ADDRESS'],cases)}

同表地址实验在每组计时前切换表内容并同步，上传时间另外落盘。部署固定策略只在建 plan 时配置一次；因此这个测试用于排除表 VA 混杂，不能把该测试的每组策略切换说成免费的生产热态操作。

## 5. 最终常量参数版：完整单请求

三个地址等权，四份输入已预热且每次请求不重新写入：

{table('const_confirm',['MINIMAX/NATIVE','MINIMAX/IDENTITY','MINIMAX/RANDOM_POOL','MINIMAX/WRONG_ADDRESS'],cases,scope='ready',address='ALL')}

每次先实际重写当前 logits，再计算 Softmax；copy 和 Softmax 的全部 kernel 一起计时：

{table('const_confirm',['MINIMAX/NATIVE','MINIMAX/IDENTITY','MINIMAX/RANDOM_POOL','MINIMAX/WRONG_ADDRESS'],cases,scope='fresh',address='ALL')}

重写输入来自四个轮换源缓冲区。独立的输入重写控制在数值检查前故意清除目标，确认该 copy 参与本次答案；常量参数版沿用相同 copy 二进制并再检查完整输出。它是缓存状态和依赖控制，不是完整 LM head GEMM，也不是逐 token 生成。

训练预测选择的邮箱页 {choice}，输入已预热且本次不重写：

{table('const_confirm',['MINIMAX/NATIVE','MINIMAX/IDENTITY','MINIMAX/RANDOM_POOL','MINIMAX/WRONG_ADDRESS'],cases,scope='ready',address=choice)}

下图为三个邮箱地址等权汇总，区别于上面的预选页 17 单点。

![Final attribution controls](figures/affinity.png)

## 6. 批量计时与主机开销

32 次完整常量参数版算子串在一个 graph 中，保留每次初始化、同步和启动间隙。使用较长事件区间检查小增量，不将它当作单请求/整模型延迟：

{table('soft_batch',['MINIMAX/NATIVE','MINIMAX/IDENTITY','MINIMAX/RANDOM_POOL','MINIMAX/WRONG_ADDRESS'],cases)}

同一个受限正点（131072、邮箱页 {choice}）在批量节奏下，MINIMAX/IDENTITY 为 **{number(target_batch,'ci9875_pct')}**（98.75% 区间），方向反转。这说明单请求的正结果有运行条件边界；批量同时改变缓存/提交节奏和可能的频率状态，不能把反转唯一归因于计时器，也不能忽略它。

所有原始单请求 C++ submit→stream-ready 主机时间也保存。最终常量参数版、输入就绪、所有地址等权的主机区间：

{table('const_confirm',['MINIMAX/NATIVE','MINIMAX/IDENTITY','MINIMAX/RANDOM_POOL'],cases,metric='host',scope='ready',address='ALL')}

主机计时从 C++ 提交到同步返回；Python 调度、建图、输入 H2D/输出 D2H 不在热态区间。GPU 阶段的百分比不能直接换算成整模型 tokens/s，主机无稳定改善时也不能把 GPU 小收益说成应用响应改善。桌面进程仍存在，CPU 未独占，未锁 GPU 频率；随机顺序、配对比较和首尾锚点降低但不能消除这些限制。

## 7. 建表、校准和接口

两个训练矩阵 worker 共 {offline:.3f} 秒（包括宿主和 I/O），CPU 匹配拟合 {fit:.3f} ms。它是一次性设备/地址模型校准，不能伪装成零成本；离线复用已有模型和每次新设备重新校准是两种不同成本合同。仅凭几十纳秒热态收益，并不能保证把数秒校准成本摊平。

三个新进程的公共接口建 plan 中位数如下，含设备输出/workspace、SM roster 前置检查、Graph 和初次数值核验，已初始化 CUDA；不含冷启动 Python/CUDA context 和设备校准：

{chr(10).join(setup_lines)}

选定邮箱页 {choice} 的描述性回本估算：

{chr(10).join(cost_lines)}

这些是 3 个初始化进程和 6 个计时进程的点估计，不是冷启动 SLA。观测到的负初始化差额仍记录，计算回本时只将它截为零，不能解释为“负成本”。逻辑邮箱区 2 MiB，为满足对齐实际分配 4 MiB；另有少量 partial/trace。若重新校准成本需要很久才摊平，就不能把微小热态增量直接包装成全生命周期净收益。

`src/softmax_plan.py:TopologySoftmaxPlan` 支持 FP32、连续、单 token、V∈{{32768,65536,131072,262144}}，明确限定这台 56-SM T10 的经验模型。输入缓冲固定，可在同一 CUDA stream 更新内容后调用 `run()`；每个并发 stream 要独立 plan/workspace。NATIVE 默认不启用亲和；实验调用 `policy='MINIMAX', backend='constant'`。默认邮箱来自冻结训练选择。输出留在 GPU，不是同步返回的 CPU 数组。接口不承诺未测尺寸、其它 GPU 或真实模型全链收益。

## 8. 完整性和统计边界

本轮 {audit['workers']} 个 worker，累计 {audit['worker_seconds']:.3f}/{audit['worker_budget_seconds']} GPU-worker 秒（含 CPU 准备、检查和落盘）。计时观测共 {audit['test_timing_observations']} 个，包含开发阶段 {audit['development_timing_observations']} 个与独立确认/控制 {audit['independent_validation_timing_observations']} 个；其中 {audit['test_batched_observations']} 个为 32 次算子的批次；合计实际算子请求 {audit['operator_requests_in_test']} 次。{audit['numerical_checks']} 项数值/接口检查通过。采样温度 {audit['temperature_range_c'][0]}–{audit['temperature_range_c'][1]}°C，功耗上限 100 W，风扇及过温保护保持。所有负例、未选 CA/CG、错误地址、最差配对和异常首尾锚点均留在 raw。

两次预期修复记录没有删除：初次 trace 夹具清零在默认 stream、计时在另一 stream，缺少显式同步，修复夹具依赖后重新全部资格；初次 Softmax cooperative 启动的动态/静态共享内存 opt-in 遗漏，原源码和二进制保存在 `support/soft_initial`。它们不算性能样本或检查通过。其余 worker 的状态与所有 sanitizer 日志由 CPU audit 逐一验证。

先取随机块内请求中位数，再计算配对 log 比；地址/形状/进程等权，bootstrap 以整个新进程为单位，共 30000 次。六进程属于同一张卡和同一天，不是六张硬件。逐形状同时保存 98.75% 区间；常量参数版另保存 99.375% 区间用于八个形状×scope 的保守审阅。多阶段属于连续研究，不能将这些区间当成覆盖整个研究历史的无条件发现概率。微小差异还需跨天、重分配和其它裁剪配置独立复现。

结论强度只限“这台 T10、冻结地址合同和这些真实执行的算子上，改变 SM 交接安排的测量效果”。物理 SM 屏蔽拓扑因果、通用 NUMA 域、成熟推理框架中的整模型加速仍未建立。
'''
 (ROOT/'reports/REPORT.md').write_text(text)
 # A compact data artifact intentionally omits the large per-block cell arrays.
 small={}
 for name in ['claim_confirm','soft_confirm','soft_panel','soft_fresh','soft_common','soft_batch','const_confirm']:
  obj=read(ROOT/f'derived/{name}.json');small[name]={key:obj[key] for key in ['results','by_address_results'] if key in obj}
 write(ROOT/'reports/RESULTS_COMPACT.json',small)
 print('REPORT_WRITTEN')
if __name__=='__main__':main()
