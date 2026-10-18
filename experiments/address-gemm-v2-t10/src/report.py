from common import *
import numpy as np

def main():
 full=read(ROOT/'derived/RESULTS.json');r=full['confirmation'];t=read(ROOT/'derived/TUNING_RESULTS.json')['tune_confirmation'];audit=read(ROOT/'derived/CONFIRMATION_AUDIT.json');sel=read(ROOT/'freeze/TUNED_RECIPES.json')['cases'];geometry=read(ROOT/'freeze/SELECTED_GEOMETRY.json');cases=['R_G002','R_G017','D13','V13'];lines=[]
 def add(x=''):lines.append(x)
 def pc(v):return f'{v:+.3f}%'
 def get(stage,cid,pol,base,metric='gpu_us'):return stage['by_case'][metric][cid][pol][base]
 add('# T10：页内地址队列、末到达块融合与强基线复验')
 add('\n本轮已经执行完毕。所有百分比表示“时间减少”：正值更快，负值更慢。GPU 主计时始终覆盖完整 GEMM 到输出完成；主机同时测 C++ 提交到同步返回。校准、建表、建图和输入传输不在热态区间内，另列实际费用。')
 a=get(t,'D13','TUNED_NATIVE','LIB');b=get(t,'R_G017','TUNED_NATIVE','OLD_NATIVE');f=get(r,'R_G017','FUSED','NATIVE')
 add(f"\n实用结果：D13（48×2048×6144）的调优普通 CUTLASS 相对 cuBLAS，GPU 用时减少 **{pc(a['reduction_pct'])}**，六进程 {a['positive_processes']}/6 获益；R_G017 的调优普通版相对旧配方减少 **{pc(b['reduction_pct'])}**。这属于形状和 split-K 配方选择收益，**不是 SM 地址拓扑的证明**。")
 add(f"\n融合在旧 R_G017 配方上确有 {pc(f['reduction_pct'])} 的完整 GPU 时间优势，六进程全部为正，但该优势必须继续与调优普通版比较。地址队列全尺寸相对原版为 {pc(r['contrasts']['gpu_us']['QUEUE_SELECTED']['NATIVE']['reduction_pct'])}；相对不看 SM 地址偏好的同队列为 {pc(r['contrasts']['gpu_us']['QUEUE_SELECTED']['QUEUE_BLIND']['reduction_pct'])}，没有形成可靠净收益。")
 add('\n## 新实现与因果对照')
 add('\n1. **页内队列**：从上轮 8 KB 任务改成 2 KB/4 KB 任务。workspace 按 4 KB 对齐，避免单个任务在第一份 partial 内跨页；其他 split 的地址类别仍需逐一核查，不能假定相同。普通 CUDA CTA 根据历史 SM 偏好先领取一类任务，空了再从另一类领取。去掉全网格同步和每 SM 48 KiB 的驻留限制。两个领取计数器由乘法核的首 CTA 重置，不增加单独清零核。所有原子操作、任务查表、重置和启动费用均包含在完整 GEMM 内。')
 add('\n2. **融合**：保留 CUTLASS Tensor Core MMA，每个输出 tile 的最后一个 split producer 完成有序 FP32 归并，省去独立 R 核。各生产线程先发布自己的 partial，CTA 同步后由线程 0 做 GPU 范围 acquire/release 到达计数；最后一个 CTA 用 `.cg` 读取 partial，归并完后复位该 tile 的计数器。没有自旋等待。输入为 FP16、累加/输出 FP32；alpha/beta 只在最终输出应用一次。')
 add('\n3. **普通直接归并**：同一向量归并计算体由普通 CUDA 网格直接处理，作为没有队列的对照。队列另设不看 SM 偏好、正向、反向、打乱地址标签控制；独立保存实际 SM/任务领取结果。')
 add('\n历史类别规则仅是待检验假设：`SM%10∈{4,5,6,7}` 与其他 SM 分成两类，地址用 `parity((VA>>12)&0x33)`。VA 位不是物理 home 节点；当前实验会测试两个方向并在真正并发的完整 GEMM 上选择方向，不能据此声称发现 GPU 物理 NUMA。')
 add('\n[CUDA 内存栅栏说明](https://docs.nvidia.com/cuda/archive/13.2.1/cuda-c-programming-guide/index.html#memory-fence-functions)说明了最后一个 block 归并所需的发布顺序与可见性要求；本实现额外使用显式 GPU 范围到达原子操作和绕过 L1 的读取。racecheck 主要检查共享内存危险，不能替代跨 CTA 全局内存协议的推理。')
 add('\n## 开发与确认分离')
 add(f"\n第一阶段用两个开发进程，在 chunk=512/1024 个 float、grid=56/112 个 CTA 的四种组合里固定选择了 **chunk={geometry['chunk']}、grid={geometry['grid']}**。之后六个新进程确认，每个新分配的地址只用 12 个校准块选择正向或反向，随后的 30 个随机测试块不参与选择；每块每策略 8 次独立同步请求。四个既有形状、两个偏移 0/69632 字节、四个输入槽。")
 add('\n第二阶段在两个额外开发进程中有限搜索：recipe 0（32×64 tile）/recipe 2（64×128 tile），split-K 2/4/8/16，普通与融合分别选最优配方。再用六个额外新进程验证，保留同配方普通版、独立调优普通版、旧版和 cuBLAS。选择器在确认数据产生之前冻结。所有形状在此前实验中已经见过，D13/V13 是人工设计尺寸，不是模型 trace；新进程复验不等于新模型任务泛化。')
 add('\n**输入隔离限制**：事后源码审计发现，两个阶段各自的开发进程 0/1 与确认进程 0/1 使用相同输入种子；64 对同配方输出 SHA256 也确认重合。`tuning.py` 冻结版顶部声称输入不重合的注释不准确，实际代码和原注释原样保留，不能据此称六进程全部为新输入。确认进程 2–5 的种子不在开发集中。以下仍完整报告六进程主结果，另列按种子是否重合划分的事后敏感性复算，没有依据时间选择或删除进程；该复算不是新增实验。')
 add('\n| 形状 | 普通最佳 recipe/S | 融合最佳 recipe/S | 开发阶段冻结的使用路径 |\n|---|---|---|---|')
 for cid in cases:add(f"| {cid} | {sel[cid]['native']} | {sel[cid]['fused']} | {sel[cid]['route']} |")
 add('\n## 旧配方上的完整耗时')
 add('\n| 案例 | 地址队列 vs 原版 | 地址队列 vs 无偏好队列 | 融合 vs 原版 | 融合获益进程 |\n|---|---:|---:|---:|---:|')
 for cid in cases:
  z=get(r,cid,'FUSED','NATIVE');add(f"| {cid} | {pc(get(r,cid,'QUEUE_SELECTED','NATIVE')['reduction_pct'])} | {pc(get(r,cid,'QUEUE_SELECTED','QUEUE_BLIND')['reduction_pct'])} | {pc(z['reduction_pct'])} | {z['positive_processes']}/6 |")
 add('\n![旧配方结果](figures/fixed_recipe.png)')
 add('\n`QUEUE_SELECTED` 使用前置校准冻结的方向，结果取自之后实际测到的对应队列核；不是在测试数据中取两方向的最小值。`FROZEN_ROUTE` 同样取开发阶段预选路径的实际测试记录。两者是已测路径的归属统计，没有伪造额外执行次数；选择在图构建时完成，热态 C++ 调用不增加逐请求搜索。')
 add('\n## 更强基线下，收益还剩多少')
 add('\n| 案例 | 调优普通 vs 旧普通 | 调优融合 vs 同配方普通 | 调优融合 vs 最佳普通 | 调优普通 vs cuBLAS | 冻结路径 vs cuBLAS |\n|---|---:|---:|---:|---:|---:|')
 for cid in cases:add('| '+cid+' | '+' | '.join(pc(get(t,cid,pol,base)['reduction_pct']) for pol,base in [('TUNED_NATIVE','OLD_NATIVE'),('TUNED_FUSED','SAME_NATIVE'),('TUNED_FUSED','TUNED_NATIVE'),('TUNED_NATIVE','LIB'),('FROZEN_ROUTE','LIB')])+' |')
 add('\n| 案例 | 旧普通 µs | 调优普通 µs | 调优融合 µs | cuBLAS µs |\n|---|---:|---:|---:|---:|')
 for cid in cases:
  vv=[next(x['median_us'] for x in t['absolute'] if x['metric']=='gpu_us' and x['case']==cid and x['policy']==pol) for pol in ['OLD_NATIVE','TUNED_NATIVE','TUNED_FUSED','LIB']];add('| '+cid+' | '+' | '.join(f'{x:.3f}' for x in vv)+' |')
 add('\n绝对时间为描述性中位数，百分比使用配对对数比，不能简单相除来替代配对结果。')
 z=get(t,'R_G017','OLD_FUSED','OLD_NATIVE');v=get(t,'V13','TUNED_FUSED','TUNED_NATIVE');vl=get(t,'V13','TUNED_FUSED','LIB')
 add(f"\n同一旧 R_G017 配方的融合优势在第二阶段为 {pc(z['reduction_pct'])}，六进程全部为正，说明约 2% 的局部收益并非只出现一次。但换成调优配方后，融合比调优普通版更慢。V13 第二阶段融合相对调优普通版为 {pc(v['reduction_pct'])}，相对 cuBLAS 仍为 {pc(vl['reduction_pct'])}；第一阶段 V13 为负且区间宽，两阶段都保留，不称为稳定通用收益。V13 的 OLD_NATIVE/TUNED_NATIVE/SAME_NATIVE 实际配方相同，标签之间的差异是不同测试位置的观测差异。")
 add('\n![更强基线](figures/strong_baselines.png)\n\n![绝对完整时间](figures/absolute_times.png)')
 add('\n| 重点比较 | GPU 时间减少 | 95% 进程 bootstrap | 主机时间减少 |\n|---|---:|---|---:|')
 for cid,pol,base in [('R_G017','TUNED_NATIVE','OLD_NATIVE'),('D13','TUNED_NATIVE','LIB'),('R_G017','TUNED_FUSED','TUNED_NATIVE')]:
  z=get(t,cid,pol,base);lo,hi=z['ci95'];add(f"| {cid}: {pol}/{base} | {pc(z['reduction_pct'])} | [{lo:+.3f}%, {hi:+.3f}%] | {pc(get(t,cid,pol,base,'host_us')['reduction_pct'])} |")
 add('\n统计单位是新进程；进程内先对每个随机块的重复取中位数，再平均配对对数比，六个进程等权。Bootstrap 以进程重采样，未做多重比较校正。单板 T10 的多个进程不是多块硬件复验，结果不外推到其他架构。')
 add('\n| 事后敏感性复算，仅确认进程 2–5 | GPU 时间减少 | 95% 进程 bootstrap | 获益进程 |\n|---|---:|---|---:|')
 for phase,cid,pair in [('confirmation','ALL','QUEUE_SELECTED/NATIVE'),('tune_confirmation','D13','TUNED_NATIVE/LIB'),('tune_confirmation','R_G017','TUNED_NATIVE/OLD_NATIVE')]:
  z=audit['sensitivity'][phase]['gpu_us'][cid][pair];lo,hi=z['ci95'];add(f"| {cid}: {pair} | {pc(z['reduction_pct'])} | [{lo:+.3f}%, {hi:+.3f}%] | {z['positive_processes']}/4 |")
 add('\n这些结果由全部原始请求重新聚合，限定依据是输入种子规则，不是性能。四进程样本仍很小；它确认本轮 D13 收益没有依赖那两个重复种子，但不能消除单卡、已见形状和固定分布的限制。审计明细在 `derived/CONFIRMATION_AUDIT.json`。')
 add('\n## 波动、校准成本与适用边界')
 for name,stage in [('页内队列/融合确认',r),('配方确认',t)]:
  for metric,a in stage['aa'].items():
   count=a.get('anchor_pairs',a.get('pairs'));add(f"\n- {name} {metric}：{count} 对 A/A，绝对变化 >5% 共 {a['abs_over_5pct']} 对，P95 为 {a['p95_abs_pct']:.3f}%；全部保留，没有排除慢态或离群请求。")
 add('\n整体 A/A 波动很大，不能只用六进程区间忽略运行状态。进一步按形状检查第二阶段 GPU A/A，并在不删数据的条件下更换 cuBLAS 参照：')
 add('\n| 案例 | A/A >5% 次数 / 360 | A/A 绝对变化 P95 | 调优普通 vs 块前 cuBLAS | vs 块后 cuBLAS | vs 按位置插值的 cuBLAS |\n|---|---:|---:|---:|---:|---:|')
 for cid in cases:
  a=audit['tuning_anchor_sensitivity']['gpu_us'][cid];cc=a['contrasts'];add(f"| {cid} | {a['aa_abs_over_5pct']} | {a['aa_p95_abs_pct']:.3f}% | {pc(cc['LIB_A']['reduction_pct'])} | {pc(cc['LIB_B']['reduction_pct'])} | {pc(cc['INTERPOLATED_LIB']['reduction_pct'])} |")
 add('\n插值仅是事后敏感性分析，不能假定真实漂移一定线性。D13 三种锚点参照均为正，按随机执行位置分层也均为正。V13 的锚点、块内位置影响明显；其融合小优势和精确百分比不应写成稳定论文结论，状态根因仍未关闭。完整位置分层结果见审计 JSON，原始数据一条未删。')
 add('\n各次队列方向校准、列表/图构造和数据初始化实际费用在 `derived/RESULTS.json` 的 setup 中。方向校准需要真实 GEMM 重复执行，不能视为免费。')
 for cid in cases:
  ss=[x for x in r['setup'] if x['case']==cid];add(f"\n- {cid}：方向校准中位数 {np.median([x['calibration_ms'] for x in ss]):.3f} ms，全部策略列表/图构建中位数 {np.median([x['graphs_and_lists_ms'] for x in ss]):.3f} ms。")
 add('\n页内任务并不保证所有 split 的部分结果属于同一地址类。原始 `mapping.json` 保存了每任务类别以及所有 split 同类的比例。识别一次孤立访问的差异，与在高并发 GEMM 中找到可复现的调度增益，是两件分别验证的事。本轮没有得到后者的可靠正证据。')
 add('\n## 实际可复用代码')
 add('\n`src/dispatch.py` 已把开发阶段冻结的路径接入既有 Engine/Data/Job 接口：D13 使用 recipe 0、split-K 2 的普通 CUTLASS；其余三个已测形状及未知形状使用 cuBLAS。构造接口只做形状查表和建图，执行复用既有 C++ 完整 GEMM 路径。`required_workspace_words` 返回所需私有中间缓冲区大小，`build_deployed` 生成可运行的 Job。四个已测形状与一个未知形状、两个输入槽均实际运行并通过输出检查。')
 add('\n没有把地址队列或融合默认开启。融合实验要求计数器与 workspace 在并发调用间独立；同一个缓冲区只支持本实验这种有序流重放。所有接口沿用本仓库的 GPU 输入已就绪约定；完整时间不含输入 H2D、结果 D2H 或 Python 框架调用开销。未知形状的 cuBLAS 回退通过了功能检查，但未声称已做广泛性能验证。')
 add('\n## 正确性、失败和账本')
 for stage in [full['development'],r,read(ROOT/'derived/TUNING_RESULTS.json')['tune_development'],t]:add(f"\n- {stage['phase']}：测试请求 {stage['counts']['test']}；数值检查 {stage['numerical_checks']}，全部通过。")
 add(f"\n第一阶段另有 {full['development']['placement_checks']+r['placement_checks']} 次任务领取/最后到达 SM 诊断。逐任务覆盖恰好一次、偏好/队列标签一致；融合每 tile 的到达序号是 0..S-1 的排列，最后写者与最终归并 SM 一致。每次有序重放后计数器复位检查通过。")
 add('\n首轮边界/alpha beta/重放检查 240 项通过；新增 split-K 2/16 检查 32 项通过。全量 memcheck、synccheck 均 0 errors。全量 racecheck 在 180 秒上限未完成，明确不是通过；后续小矩阵四次新增核定点 racecheck 完成，0 errors、0 warnings。第一次定点工具调用参数格式错误，在 CUDA 执行前被拒绝，日志和账本保留。以上均未改变性能代码或删改慢数据。')
 res=full['resources'];add(f"\n新账本实际 {res['worker_seconds']:.3f} 秒 / 1800 秒 GPU-worker 上限，包含失败检查、初始化与 CPU 等待；采样温度 {res['sampled_temperature_range_c']}°C，功耗上限始终 100W，保留风扇和过温保护。旧轮账本未追加。")
 add('\n完整原始请求、条件化与校准记录、所有四种队列配置、所有 16 种普通/融合配方、正负结果、冻结选择、二进制/SASS、编译日志、实际图、校验摘要和输出 SHA256 均保留。未保存所有完整输出矩阵；数值检查包括完整 FP32 参考和预先固定的 FP64 子块。')
 add('\n## 结论与下一步')
 add('\n现在可以复用的是有限形状上的 GEMM 配方选择。地址队列这条实现没有成功；融合在旧配方上的小优势不能脱离更强普通配方和 cuBLAS 单独宣传。论文若以 NUMA/SM 地址拓扑为主张，仍缺少真实并发成本的可复现预测及强基线下的净收益，不能用本轮配方调优结果补上这个证据缺口。')
 add('\n后续应先把新的强基线固定下来，再考虑更能重复使用局部中间结果的融合算子，或有可控数据分区的 producer–consumer 链。继续寻找单次最佳延迟不足以支持论文结论。')
 add('\n纯 CPU 复算：在解压目录运行 `python3 src/recompute.py`，需要 NumPy，不需要 CUDA/PyTorch；它重建地址类别与实际任务覆盖，重新计算开发选择、校准方向和全部结果。绘图另运行 `src/figures.py`，需要 Matplotlib。GPU 重跑需要本机现有 CUDA/PyTorch/cuBLAS、CUTLASS 和 T10 环境，并另建运行目录；本包不自动追加实验。')
 (ROOT/'reports/REPORT.md').write_text('\n'.join(lines)+'\n');print('REPORT_PASS')
if __name__=='__main__':main()
