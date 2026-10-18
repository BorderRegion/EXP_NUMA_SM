from common import *
import numpy as np
import pandas as pd
import shutil

def table(headers, rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']+
        ['| '+' | '.join(map(str,r))+' |' for r in rows])
def pct(x):return f'{x:+.3f}%'
def ci(x):
    fmt=lambda v:f'{v:+.5f}' if 0<abs(v)<.001 else f'{v:+.3f}'
    return '['+fmt(x[0])+', '+fmt(x[1])+']'
def run():
    audit=read(ROOT/'derived/FINAL_AUDIT.json')
    full=read(ROOT/'derived/full_summary.json')
    net=[x for x in read(ROOT/'derived/NET_RESULTS.json') if x['metric']=='outer_wall_s']
    phases=['confirm','shared','fast'];data={p:read(ROOT/f'derived/{p}_operator.json') for p in phases}
    scopes=['ready','fresh','batch','freshbatch'];sl={'ready':'热输入单次','fresh':'重写后单次','batch':'热输入连续32次','freshbatch':'每次重写并连续32次'}
    names={'confirm':'原主实验','shared':'共用Graph复验','fast':'低开销校准复验'}
    def row(p,s,c='ALL_ADDR',ctrl='IDENTITY'):
        return next(x for x in data[p] if x['V']==131072 and x['page']==17 and x['scope']==s and x['metric']=='gpu_us' and x['candidate']==c and x['control']==ctrl)
    hierarchy=[]
    for page in [0,17,257]:
        a=next(x for x in full if x['page']==page and x['unit']=='ns' and x['comparison']=='same_tpc/cross_gpc')
        b=next(x for x in full if x['page']==page and x['unit']=='ns' and x['comparison']=='same_gpc_other_tpc/cross_gpc')
        hierarchy.append([page,f"{a['class_mean']:.1f}",f"{b['class_mean']:.1f}",f"{a['cross_mean']:.1f}",pct(a['gain_pct'])+' '+ci(a['ci95']),pct(b['gain_pct'])+' '+ci(b['ci95'])])
    operators=[]
    for p in phases:
        for s in scopes:
            a=row(p,s);operators.append([names[p],sl[s],pct(a['gain_pct']),ci(a['ci95']),ci(a['ci_primary']),f"{a['positive_processes']}/6"])
    netrows=[]
    for s in ['batch','freshbatch']:
        for c in ['IDENTITY','RND07' if s=='batch' else 'RND03','ALL_WRONG','ALL_POOL']:
            a=next(x for x in net if x['scope']==s and x['control']==c)
            netrows.append([sl[s],c,pct(a['gross_gain_pct']),pct(a['gain_pct']),ci(a['ci_net_family']),f"{a['positive_processes']}/6"])
    setup=read(ROOT/'derived/FAST_SETUP_TIMES.json');old=read(ROOT/'derived/SETUP_COST_BOUNDS.json')
    oldmedian=np.median([x['gross_setup_ms'] for x in old if x['process'].startswith('shared_')])
    newmedian=np.median([x['total_setup_ms'] for x in setup])
    correlations=next(x for x in read(ROOT/'derived/shared_micro_summary.json') if x['page']==17 and x['unit']=='cycles' and x['comparison']=='same_tpc/cross_gpc')['residual_correlations']
    # Complete flat tables preserve every reported condition, including negative results.
    pd.concat([pd.DataFrame(read(ROOT/f'derived/{p}_operator.json')).assign(stage=p) for p in ['dev']+phases],ignore_index=True).to_csv(ROOT/'derived/ALL_OPERATOR_RESULTS.csv',index=False)
    topo=read(ROOT/'freeze/HARDWARE_TOPOLOGY.json');sm=topo['global_sm_order']['entries']
    hierarchy_maps=[]
    for worker in sorted(RUN.iterdir()):
        q=worker/'micro/allocation_maps.json'
        if not q.exists():continue
        for m in read(q)['maps']:
            consumers=m['consumer_per_producer'];counts=[0,0,0]
            for i,j in enumerate(consumers):
                a,b=sm[2*i],sm[j]
                k=0 if a['global_tpc']==b['global_tpc'] else 1 if a['gpc']==b['gpc'] else 2
                counts[k]+=1
            hierarchy_maps.append(dict(process=worker.name,page=m['page'],policy=m['policy'],same_tpc=counts[0],same_gpc_other_tpc=counts[1],cross_gpc=counts[2]))
    pd.DataFrame(hierarchy_maps).to_csv(ROOT/'derived/MAPPING_HIERARCHY.csv',index=False)
    decision=dict(status='EXPERIMENT_COMPLETE_NOT_DEPLOYED',default='IDENTITY',unchanged_kernel_sha256=PROTOCOL['baseline_hashes']['build/baseline/softmax_const.so'],
        topology_address_specific_net_acceleration_established=False,
        reason='Warm segmented-session net beats fixed pairing but fails frozen random, wrong-address and pooled-address controls. Copy-before-each-request is not robustly positive.',
        accounting='Measured request chunks + calibration + all candidate updates; excludes common graph construction, inter-chunk research I/O and 2 conditioning replays per chunk. Not full LLM service elapsed time.')
    write(ROOT/'reports/DECISION.json',decision)
    text=f'''# T10 真实拓扑与地址亲和调度实验结果

本轮已完成真实 TPC/GPC 分层测量、原快核上的同分配地址校准、Graph 对象控制，以及计入校准费用的百万次请求测试。**同 TPC 的孤立邮箱往返略快，但同 GPC 不同 TPC 没有显示优势；目前仍未建立地址亲和调度本身带来的可靠净加速。**

最接近目标的结果是：低开销校准后，热输入长测试相对原固定配对的净速度比为 **+0.418%**，六个进程中五个为正。它同时输给冻结随机配对、错误地址及混合地址对照；每次重写输入时相对原配对为 **−0.214%**，区间跨零。原快核和默认固定配对保留，不把这一结果升级为通用 NUMA 优化。

检查日期为 2026-10-18；本轮证据目录为 `runs/{RUN.name}`。所有百分比均为 `100 × (对照耗时 / 候选耗时 − 1)`，正数表示候选更快；它与“耗时下降百分比”并不完全相同。+0.418% 对应约 0.416% 的配对几何平均耗时下降。

## 硬件分组与测量边界

本机 Tesla T10 是 56 SM 的 TU102GL，计算能力 7.5，驱动与 GSP 为 580.178.04。物理 GPC 0–5 启用 SM 数为 **10、12、12、10、0、12**，每个启用 TPC 均有两个 SM。GPC 掩码为 0x2f；六个 TPC 掩码为 0x3e、0x3f、0x3f、0x1f、0、0x3f。逻辑到物理 GPC 映射为 0→0、1→1、2→2、3→3、4→5。

每个 GPU worker 都重新读取驱动拓扑，并与冻结快照逐项一致。分组来自 RM GET 接口；逐 SM 表见 `support/SM_TO_GPC_TPC.csv`，冻结原始值见 `freeze/HARDWARE_TOPOLOGY.json`。物理 GPC4 整组关闭不代表已经知道硅片坐标、实际互联跳数或关闭原因。逻辑局部 TPC 编号也没有被擅自解释为物理掩码位号。可选 PHYS_GPC_MASK 查询返回权限不足，未使用其无效掩码。

原基线 `(0,1)、(2,3)、…、(54,55)` 的 **28 对已经全部位于同 TPC**。因此，把它改成“同 TPC 优先”本身不能再带来新的局部性收益。组定义依据 [NVIDIA 同版本 GR 接口](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/580.178.04/src/common/sdk/nvidia/inc/ctrl/ctrl2080/ctrl2080gr.h) 和 [floorsweeping 映射接口](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/580.178.04/src/common/sdk/nvidia/inc/ctrl/ctrl2080/ctrl2080grmgr.h)。

测量使用 8 字节全局内存邮箱，包含轮询、release/acquire、数据传递和应答。起止时间都取自发送 SM，避免直接相减不同 SM 的时钟；另保留 globaltimer 纳秒和 clock64 周期。**这些数值是完整邮箱往返时间，不能称为裸 SM 连线或单向访问延迟。**

## 同 TPC 有小优势 同 GPC 没有显示局部优势

完整方向补测覆盖 56×55 个非自身有向 SM 对，三个地址页、每页两轮、六个独立进程；每个进程 18,480 次 launch。按发送 SM 配对比较三类目标，避免各 GPC 数量不一致直接改变权重。

{table(['邮箱页','同 TPC 均值 ns','同 GPC 不同 TPC ns','跨 GPC ns','同 TPC 对跨 GPC 速度比及95%区间','同 GPC 不同 TPC 对跨 GPC及95%区间'],hierarchy)}

页17中，同 TPC 约 1160.6 ns，跨 GPC 约 1174.3 ns，同 GPC 不同 TPC 约 1178.9 ns。差别是十几纳秒量级，不支持“跨 GPC 就明显更远”的简单 CPU NUMA 类比。表内均值是类均值，速度比则先按发送者、进程取几何平均，因此两者不能直接用总体均值相除复现。

![真实层级的往返差异](figures/01_hierarchy.png)

并发会改变结论。在主确认阶段页17的 28 对同时通信实验中，相对同 TPC 固定配对，按每轮最慢一对统计，固定同 GPC 不同 TPC 配对快约 1.43%，固定跨 GPC 配对快约 1.46%，ALL_ADDR 快约 3.24%。这些是通信微测的结果，不是完整 Softmax 提速。孤立访问更近与并发尾延迟更低并非同一个目标；当前数据不能区分共享资源竞争、缓存行为和其他执行状态各自的贡献。

训练与独立验证之间的地址残差排序也并不稳定。按用于拟合的周期度量，一个主确认进程的三页相关系数约 0.93–0.94，其他多个进程接近零；共用 Graph 复验六进程的页17相关系数从约 {min(correlations):.3f} 到 {max(correlations):.3f}。全部系数、固定效应回归、GPC 分组均值及56×56矩阵均保留。跨进程不应共用一张“永久延迟地图”。

## 已接入快核的调度实现

所有方案使用相同的原 `softmax_const.so`，SHA256 为 `{decision['unchanged_kernel_sha256']}`。完整 Softmax 包括全部规约、归一化和输出，不只计邮箱片段。每个 SM 一个128线程 CTA，56 CTA 协作，48 KiB shared memory；原工作条带和最后到达者归并机制保持。

只改变按值传入的56个整数配对参数，共224字节。热路径没有新增调度 kernel、抢任务队列、显存分配或配对表上传。校准使用与后续算子完全相同的邮箱 allocation，而不是另分配一块显存后迁移相对页号。

主方案用两轮训练中较大的边代价进行瓶颈匹配，再以总和打破并列；GPC_ADDR 限制在真实同 GPC 内，ALL_ADDR 允许跨 GPC。验证和完整算子时间均不参与拟合。对照包含固定同 TPC、同 GPC 不同 TPC、跨 GPC、八套固定随机配对、错误地址拟合和三页混合拟合。最强随机对照只由两个开发进程选出，在六个确认进程之前冻结。所有配对的实际同 TPC／同 GPC／跨 GPC 数量见 `derived/MAPPING_HIERARCHY.csv`。

为控制 CPU 和 Graph 差异，补充实现共用同一 executable graph、stream 和计时 event；每个输入槽保持句柄不变，只通过官方 [CUDA Graph 参数更新接口](https://docs.nvidia.com/cuda/archive/12.8.2/cuda-driver-api/group__CUDA__GRAPH.html) 替换参数，并核对读回的224字节。A/A 也执行更新。参数更新在 CPU 测时，单列计费。

## 完整算子上的正负结果

下表是词表131072、页17、ALL_ADDR 相对原固定配对的完整 GPU 时间。每阶段均有六个新进程。原主实验没有被后续补充实验替换。主实验和两个复验的32项对照族分别给出99.84375%区间；跨阶段探索没有被包装成一次全局预注册检验。

{table(['阶段','调用方式','速度比','95%区间','32项族区间','正向进程'],operators)}

共用 Graph 阶段的热输入单次是较强的条件性正结果：相对固定配对、冻结随机、错误地址、混合地址的保守区间均为正。但连续调用和重写输入不能保持同样结论；例如共用 Graph 的重写后连续方案相对错误地址配对反而慢约0.209%。

A/A 仍有偏差：共用 Graph 阶段热输入单次约 −0.440%，连续32次约 −0.027%，重写后连续约 +0.102%；后者与候选约 +0.090% 的小优势同量级。不能将每个千分之几的正数都理解为硬件拓扑规律。所有 first-after-switch、conditioning、test 数据都保留，主统计按事先规定使用 test，未删除表现不好的进程或采样。

![所有算子阶段的主要结果](figures/02_operator_stages.png)

主实验另外覆盖词表65536，以及131072的页0、257。全部条件和对照已汇总到 `derived/ALL_OPERATOR_RESULTS.csv`，没有只保存本表页17的结果。重写模式是从预生成 logits 复制到工作缓冲区，并将 copy 耗时计入；它没有执行真实上游投影层，也没有每次生成全新的 token 数据。

## 校准开销与百万次请求净账单

原分配校准的 gross 准备区间中位数约 {oldmedian:.1f} ms，包含研究记录 I/O；GPU排队加Python拟合的下界也已保存。新实现同时测28对，采用两轮随机 Latin 排列、每轮三页28个移位，共168次 launch，完整覆盖每页784条边；CPU匹配改用编译代码，并通过16项Python及小规模穷举交叉检查。

新完整校准耗时为 {min(x['total_setup_ms'] for x in setup):.2f}–{max(x['total_setup_ms'] for x in setup):.2f} ms，中位数 **{newmedian:.2f} ms**，其中拟合约5–6 ms。该区间包含计划生成、必要分配与上传、GPU探测、回传、校验及可用主机参数构造，结束于研究落盘之前。因为并发测量口径也改变了，不能把两者比值称为同一校准任务的纯实现加速，更不能把减少准备时间算作 GPU NUMA 加速。

每种方案、每个进程、每种调用方式测 **1,048,576 次完整 Softmax**，分16个随机顺序块，每次 Graph 含32次算子。主计费为实测请求块外层墙钟之和，再给候选加上本进程全部校准及16次参数更新；所有对照免准备与更新费用。这是偏向对照的保守部署门槛，错误地址／混合地址本身也需要拟合，因此它们的下表净差不是公平同成本的纯地址因果估计；旁列毛速度比用于区分。

{table(['调用方式','对照','不扣准备的毛速度比','扣费后净速度比','8项族99.375%区间','正向进程'],netrows)}

热输入候选每百万次请求的六进程平均实测请求块约7.0788秒，校准及更新平均38.335毫秒，合计7.1171秒；原固定配对约7.1467秒。六进程净速度比分别为 +0.679%、+0.069%、+0.921%、−0.078%、+0.387%、+0.531%。按各进程本次平均节省量线性推算，对原配对的回本点约40万–125万次；这是外推，不能保证后续状态不变。

即使先不扣准备，热输入候选对混合地址也是 −0.086%；对随机／错误地址只有约 +0.217%／+0.201%。因此目前的障碍包括特定地址的辨别力和开销，不只剩“再多跑一些次数摊薄校准”。

![计入校准的请求块净账单](figures/04_net_sessions.png)

计费边界需要明确：外层墙钟包含每块调用、同步和计时结果提取；不包含共同 Graph 构造、块间研究落盘，以及每块前两次 conditioning Graph replay。它是**受控请求块耗时加部署准备账单**，不是从服务初始化到最后一个真实 LLM token 的不间断总墙钟。GPU event、launch-to-output 和外层墙钟三种视图全部保存；不能用近似回本点替代真实服务端到端验证。

## 审计与复现

本轮 {audit['workers']} 个 GPU worker 全部完成，累计 {audit['worker_seconds']:.3f}/{audit['budget_seconds']} GPU-worker 秒。这个预算口径含 worker 内CPU准备和I/O，不是纯GPU活跃秒。完成 {audit['numerical_checks']:,} 项数值检查、{audit['graphs_checked']:,} 项Graph检查；常规阶段 {audit['timing_observations']:,} 条计时观测，其中 {audit['test_observations']:,} 条为正式 test。另有 {audit['fixed_session_graph_replays']:,} 次长测试 Graph replay，覆盖 {audit['fixed_session_operator_requests']:,} 次算子请求。这些请求不是统计上独立的六千万个样本；推断单位始终是六个进程。

微测共 {audit['micro_launches']:,} 次 launch、{audit['micro_records']:,} 条记录，检查实际 SM roster、起止SM、握手数、收发值和错误位。原核的 memcheck、synccheck、racecheck，以及两个新CPU管理路径的 memcheck 均通过。数值检查在规定的运行前后和资格测试点执行，没有声称每一次长测试请求都单独拷回检查。

100 W 上限及风扇／过温保护保持；采样温度 {audit['temperature_min']}–{audit['temperature_max']}°C，停止阈值82°C。时钟未锁定，桌面远程服务仍占GPU；遥测与块内随机顺序缓解但不能消除状态混杂。所有原始异常和负数保留，没有结果依赖的提前停止。

工程异常记录：首次主实验CPU分析缺pandas，安装2.3.3后继续，未改GPU算法；共用Graph帮助库首次编译选到旧CUDA头，执行前改用匹配头；快速匹配首次编译的缩进警告修正于冻结前；快速阶段通用分析器寻找旧格式 `validation_cycles` 失败，GPU数据已完整写入，改由独立 `analyze_fast.py` 读取实际Latin格式。失败日志原样保留，不把CPU后处理失败记作GPU通过或悄悄删除。

完整包含源码、精确使用的二进制、冻结协议、逐次原始记录、所有映射、遥测、日志和五组PNG/PDF图。纯CPU复算入口为 `src/recompute.py`；先验证包内哈希，再复算统计和审计。时间戳清单用于恢复ZIP可能损失的纳秒时间，因为原gross准备区间包含文件时间证据。详见 `README_REPRODUCE.md`。

## 当前判断与后续验证的切入点

这轮完成了从真实拓扑、同allocation校准到原快核配对的实现链路，也把准备开销压到几十毫秒。结论仍是：**同 TPC 微小孤立优势真实可测，稳定 GPC NUMA 域和地址特异净收益尚未建立。** 默认仍为原固定配对；新的研究代码显式运行，不替换现有快核。

下一步最值得检验的是完整通信关键路径：28对同时通信、最后到达者归并、输入重写和缓存状态是否改变真正瓶颈。需要在固定归并角色和工作量下，让正确地址映射持续胜过相同成本的错误地址、混合地址和盲配对，再到真实 decoder 生成的新 logits 上验证。一味把SM分到同GPC，或继续在孤立邮箱矩阵上找更低的单边数值，当前证据不支持。

本结果可支持一项受控的硬件行为与优化边界研究；它还不能支撑“发现通用GPU NUMA域并获得LLM净提速”的论文主张。论文价值取决于能否把并发竞争、关键路径和地址特异性之间的因果链补上，不能仅由不均匀屏蔽或某个正百分点决定。
'''
    (ROOT/'reports/REPORT.md').write_text(text)
    (ROOT/'reports/REVIEW_QUESTIONS.md').write_text('''# 本轮结论需要接受的质疑

1. 同TPC约1%的优势来自全局邮箱往返，是否包含轮询、缓存和调度状态，而非物理互联距离？本轮没有单向物理链路测量。
2. 原固定配对已经全部同TPC；跨GPC调度在并发下有时反而更好。关键因子是否是共享资源竞争而非距离？
3. 每次新分配均校准仍出现训练验证残差排序不稳定。几十毫秒的校准结果有效期有多长？
4. 长测试对混合地址的毛速度比已为负。如何证明正确地址本身提供信息，而不是任何配对扰动都能影响尾部归并者？
5. 对照免校准费是保守部署门槛，不是公平同成本的地址因果对照。需要同时查看毛结果，不能把扣费后的失败直接解释为所有地址效应不存在。
6. 共用同一Graph后A/A仍有千分级偏差。六进程自助区间和多阶段探索是否足够支持如此小的收益？这里没有全研究历史统一的显著性控制。
7. net账单排除了共同Graph构造、块间落盘和conditioning；新数据来自固定输入环及复制，尚非真实decoder持续产生logits。能否在不中断的真实调用链里保持净收益？
8. 100W恒定但SM频率未锁，温度最高79°C且桌面服务仍在。状态漂移与历史负载能否解释部分差异？所有遥测保留供复核。

目前不替换原快核或默认配对。下一轮若继续，应冻结完整通信图、输入生成方式、同成本控制和端到端计费边界，再收集新进程数据；不能从这批确认结果重新选映射并当作独立验证。
''')
    print('REPORT COMPLETE')

if __name__=='__main__':run()
