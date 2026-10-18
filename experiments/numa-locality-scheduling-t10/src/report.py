from common import *
import numpy as np,math
def pct(x):return f"{x['time_reduction_pct']:+.3f}%"
def ci(x,key='ci95'):return '['+', '.join(f'{a:+.3f}%' for a in x[key])+']'
def main():
 first=read(ROOT/'derived/RESULTS.json');v=read(ROOT/'derived/VECTOR_RESULTS.json')['vector_confirmation'];prot=read(ROOT/'freeze/PROTOCOL.json');sel=read(ROOT/'freeze/VECTOR_SELECTION.json')['cases'];api=read(RUN/'verify_public_api/verification.json');res=first['resources'];lines=[];add=lines.append
 add('# T10：借鉴 CPU NUMA 调度，控制 kernel 开销的 GQA 解码优化\n\n日期：2026-10-18（Asia/Shanghai）。完整实验、强基线复验与可调用接口已完成。百分比均为配对完整区间的**用时减少**，正值更快；不同阶段不可相加，也不可与上一轮百分比相乘推断未测端到端收益。')
 x=v['contrasts']['append']['gpu_us']['ALL']['ROUTE/STRONG_OLD'];add(f'\n最终选定的 16 字节 KV 搬运版本，在“KV 写入 + Attention”完整 GPU 区间，相对开发阶段选出的较快旧实现，等权几何汇总 {pct(x)}，95% 进程 bootstrap {ci(x)}。本轮不把该收益归因于 NUMA；带地址偏好的版本继续单独对照。')
 add('\n## 从 CPU NUMA 借鉴了什么\n\n[Linux NUMA 说明](https://docs.kernel.org/mm/numa.html)把就近分配、减少跨节点迁移与负载均衡作为相关但不同的机制；[内存策略文档](https://www.kernel.org/doc/html/latest/admin-guide/mm/numa_memory_policy.html)说明策略与已有页迁移的区别。本机 CPU 只有一个 NUMA 节点（`support/host_lscpu.txt`），不是 CPU 双节点对照实验。T10 也不能直接把 SM 绑定到指定物理内存节点。')
 add('\n据此分别测试：每次领取 1/4/8/16 页的粗粒度领取；固定连续/物理页排序的分片；只读 KV 的双地址副本，由 CTA 按所在 SM 选择；最后是降低每次共享 KV 搬运的指令开销。前三者测试局部性与调度代价，最后一项针对观察到的开销，不是新的拓扑证据。没有修改主机调度器、关闭温控或把虚拟地址类称为物理 home 节点。')
 add('\n## 工作负载与计时边界\n\n输入是有独立种子/哈希的合成 FP16 Q/K/V。分页 KV 布局 `[physical_pages, Hkv, 16, 128]`，页表随机排列；每份 KV-head 页恰为 4 KiB，适用于这轮虚拟地址分类假设。数学为完整 GQA decode Attention，FP32 稳定 softmax/归并，FP16 输出。不是运行真实模型权重、RoPE/投影、完整 token 解码或实测 token/s。')
 add('\n| 案例 | B / Hq / Hkv / D / 最大 L | Attention / 写入阶段候选 | 强旧对照（Attention / 写入） |\n|---|---|---|---|')
 for c in prot['cases']:
  cid=c['id'];s=sel[cid];add(f"| {cid} | {c['B']} / {c['H']} / {c['HK']} / {c['D']} / {c['L']} | {s['attention']['candidate']} / {s['append']['candidate']} | {s['attention']['strong_old']} / {s['append']['strong_old']} |")
 add('\n批量四条长度为 4096/3073/2049/1027。两偏移为 0/65536 字节，4 个 Q 槽。调度/副本阶段与向量阶段各先用两个开发进程冻结选择，再用六个新进程、30 个随机块×6 次重放确认；独立 KV 维护复验沿用已冻结的调度/副本选择。核心与 KV 更新阶段分别选择直接或无 SM 偏好的队列；较快旧实现也在开发阶段从旧直接核、旧无偏好队列、上一轮部署版本中预选。全部开发与确认输入区间分离并重算哈希，禁止按确认结果改参数。')
 add('\n计时沿用同一 C++ CUDA Graph 包装器，记录所有 kernel、启动、原子领取、归并/复位与可选 KV 写入；同时记录 C++ 提交至输出就绪时间。热输入及已建图为前提，不含 Python 调用、H2D/D2H、缓存分配和 plan 构建。正式 KV 更新在固定有效长度 `length-1` 处反复写入同值，资格检查另覆盖改变值、尾页和全缓存一致性；不是逐 token 增长吞吐实验。')
 add('\n## 最终完整耗时结果\n\n| 案例 | Attention vs 强旧对照 | 写入+Attention vs 强旧对照 | 写入阶段 98.75% 区间 | 写入 vs 上轮部署 | 获益进程 |\n|---|---:|---:|---|---:|---:|')
 for c in prot['cases']:
  cid=c['id'];a=v['contrasts']['attention']['gpu_us'][cid];b=v['contrasts']['append']['gpu_us'][cid];z=b['ROUTE/STRONG_OLD'];add(f"| {cid} | {pct(a['ROUTE/STRONG_OLD'])} | {pct(z)} | {ci(z,'ci98_75_four_case')} | {pct(b['ROUTE/PREVIOUS'])} | {z['positive_processes']}/6 |")
 add('\n![最终完整区间收益](figures/final_gain.png)\n\n区间按进程 bootstrap；98.75% 区间用于四个案例比较的 Bonferroni 名义校正，不是对无限次探索或全部辅助对照的整体误差保证。随机块先取重复中位数，再算配对对数比、进程等权。六个进程是同一块 T10，不等于六块独立 GPU。')
 add('\n| 案例 | 写入阶段：强旧 / 新核中位 µs | 相同调度旧核→新核 | 主机就绪 vs 强旧对照 | 上轮部署→新图 kernel 数 |\n|---|---|---:|---:|---|')
 def absolute(cid,policy,metric='gpu_us',mode='append'):return next(x['median_us'] for x in v['absolute'] if (x['case'],x['policy'],x['metric'],x['mode'])==(cid,policy,metric,mode))
 for c in prot['cases']:
  cid=c['id'];z=v['contrasts']['append']['gpu_us'][cid];h=v['contrasts']['append']['host_us'][cid];nk=v['kernel_counts'][cid+'/append'];route=sel[cid]['append']['candidate'];add(f"| {cid} | {absolute(cid,'STRONG_OLD'):.3f} / {absolute(cid,'ROUTE'):.3f} | {pct(z['ROUTE/SAME_OLD'])} | {pct(h['ROUTE/STRONG_OLD'])} | {nk['PREVIOUS']}→{nk[route]} |")
 add('\n绝对时间仅作描述，不能用两列中位数相除替代配对估计。上轮已有 KV 融合已纳入强对照，GQA8 的旧无偏好队列也纳入，避免把旧优化重新算成新收益。')
 add('\n## 这次究竟改了什么，开销有多大\n\n最终内核相对原始 Attention/原始写入融合源，各只改动一处 KV 全局内存到共享内存的复制循环：2 字节标量搬运改成对齐 16 字节向量搬运；分页、QK、softmax、归并和调度逻辑不变。`support/vector_core.patch` 与 `vector_append.patch` 保存精确差异。代表性 D128/G4 内核的 SASS 从 `LDG.E.U16` 变成 `LDG.E.128`，出现 `STS.128`；搬运循环迭代次数减少。这支持搬运指令开销下降的解释，缺少硬件计数器，不能将全部收益分解为单一硬件事件。')
 add('\n[NVIDIA CUDA 最佳实践](https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/index.html)中的内存访问优化是相关既有方法；向量化本身不是新算法。编译日志未见 spill。最终不复制 KV，不新增调度/清零 kernel；KV 更新与 Attention 仍可融合。部分形状用静态分片，部分用无 SM 偏好的动态领取。没有强行启用地址匹配。')
 add('\n## 地址偏好的证据与负结果\n\n| 案例 | 向量核 MATCH vs BLIND（写入阶段） | vs INVERT | vs SHUFFLE |\n|---|---:|---:|---:|')
 for c in prot['cases']:
  z=v['contrasts']['append']['gpu_us'][c['id']];add(f"| {c['id']} | {pct(z['VECTOR_MATCH/VECTOR_BLIND'])} | {pct(z['VECTOR_MATCH/VECTOR_INVERT'])} | {pct(z['VECTOR_MATCH/VECTOR_SHUFFLE'])} |")
 add('\n![地址偏好控制](figures/address_controls.png)\n\nMATCH 使用历史 `SM%10∈{4,5,6,7}` 与 `parity((VA>>12)&0x33)`；INVERT 翻转方向，SHUFFLE 保留每头类别数量但打乱页标签，BLIND 按 worker 奇偶领取而不看 SM。BLIND 与 MATCH 可能还有领取分布差异，必须联合其他控制解读。即使单个对照略正，也不能把向量化的大幅收益计入地址拓扑贡献。本轮没有新测物理 SM 间距离或证明芯片物理连线。')
 add('\n第一阶段所有结果仍保留：\n\n| 案例 | 开发预选路线 | Attention vs 原快核 | 加 KV 更新后 vs 上轮部署 |\n|---|---|---:|---:|')
 early=read(ROOT/'freeze/SELECTION.json')['cases']
 for c in prot['cases']:
  cid=c['id'];add(f"| {cid} | {early[cid]['route']} | {pct(first['confirmation']['contrasts']['gpu_us'][cid]['ROUTE/LEGACY'])} | {pct(first['append']['contrasts']['gpu_us'][cid]['ROUTE/PREVIOUS_DEPLOYED'])} |")
 add('\n![先前路线的完整结果](figures/earlier_routes.png)\n\n短序列双副本只读部分约 2% 优势，在计入写入并使用上轮融合基线后消失；地址相对反向控制也不明确。双副本本身需要两倍权威 KV 存储，实验并存原缓存作对照时合计三倍；初始化 GPU/墙钟时间在原始 mapping/setup 中保留。粗粒度路线没有普遍优于原快核；GQA8 的动态领取正例也有旧无偏好队列这个更强替代。未删除这些退步或把它们藏进汇总。')
 add('\n## 可调用接口、准备成本与适用边界\n\n`src/locality_plan.py` 提供 `LocalityPlan`，输入原布局 GPU 缓存、Q、页表、有效长度及可选新 KV。构造阶段分配 workspace、必要时建页类别表；`launch()` 使用当前 PyTorch stream，不分配显存、不重建表，可捕获进 CUDA Graph。16 字节加载要求 K/V 指针 16 字节对齐。并发调用需各自 workspace，可写末页必须私有/COW，所有输入指针持续有效。')
 add('\n页表地址和条目改变时必须重建 plan；允许有效长度在固定容量内变化，但性能只对报告形状与长度有证据。真实模型中动态页分配、共享页、切换请求、图重建的成本尚未验证。默认部署门槛使用本轮确认结果进行保护，因此不是另一个独立的路由性能 holdout。双副本不作为可直接替代的可变缓存 API 暴露。')
 add('\n| 案例 | 实际默认路线（写入） | 模块已加载时 plan 构造中位 ms | 参考回本请求数 |\n|---|---|---:|---:|')
 deploy=read(ROOT/'freeze/DEPLOYMENT_POLICY.json')['cases']
 for c in prot['cases']:
  cid=c['id'];times=[x['constructor_wall_ms'] for x in api if x['case']==cid and x['append'] and x['policy']=='DEPLOY'];setup=float(np.median(times));delta=absolute(cid,'STRONG_OLD')-absolute(cid,'ROUTE');breakeven=math.ceil(setup*1000/delta) if delta>0 else None;add(f"| {cid} | {deploy[cid]['append']} | {setup:.3f} | {breakeven if breakeven is not None else '无'} |")
 add('\n表中构造时间在 CUDA 环境和模块已加载后测量，不含 CUDA context 初始化；首次模块装载样本另在 raw 保留。回本数仅为这次新 plan 构造成本除以描述性中位 GPU 节省的粗估，未抵扣旧 plan 也需要的初始化，未计框架/动态请求成本；不是已测模型端到端收益。两次构造样本及首次模块装载等成本全部见接口验证 raw，不能把一次性准备称为免费。')
 add('\n## 验证、波动与可复算性\n\n| 案例 | 写入阶段 A/A >5% / 360 | A/A P95绝对差 | 新路线 vs 块前 / 块后锚点 |\n|---|---|---:|---|')
 for c in prot['cases']:
  cid=c['id'];a=v['aa']['append']['gpu_us'][cid];b=v['anchors']['append']['gpu_us'][cid];add(f"| {cid} | {a['over5']}/360 | {a['p95_abs_pct']:.3f}% | {pct(b['ANCHOR_A'])} / {pct(b['ANCHOR_B'])} |")
 add('\n没有过滤慢态、异常块或负例。100 W 固定功耗不等于锁定时钟，状态波动仍在；置信区间不覆盖所有外部状态变化。候选与基线使用同一进程、同一输入和计时方法做随机块配对，并给出前后锚点敏感性。')
 counts={k:first[k]['counts']['test'] for k in ['development','confirmation','append']};vr=read(ROOT/'derived/VECTOR_RESULTS.json');counts.update({k:vr[k]['counts']['test'] for k in ['vector_dev','vector_confirmation']});add('\n| 阶段 | 正式请求 |\n|---|---:|')
 for k,n in counts.items():add(f'| {k} | {n} |')
 add(f"\n正式确认合计 {counts['confirmation']+counts['append']+counts['vector_confirmation']} 次，开发请求另计。第一阶段 212 项资格与 22 次定位检查、向量版 180 项资格检查、80 次实际形状任务定位/覆盖检查、96 项公开接口检查通过。数值阈值沿用相对 Frobenius≤2e-3 与逐元素≤3e-4+3e-3|ref|，第一 batch/head 另用全序列 FP64 参考。改变 KV 值及全缓存非目标位置不变均验证；输出哈希保留，未保存全部输出张量。")
 add('\n两版 memcheck/synccheck 0 errors；向量版 D128/G4/G8 定点 racecheck 0 errors、0 warnings。工具通过不是任意并发安全证明；仍需遵守 plan/COW/同流契约。最初生成器重复分号导致的编译错误记录保留，修复发生在任何 GPU 数据之前。后续向量优化是机制改变并重新冻结，不是按确认数据重新挑选参数。')
 add(f"\n账本累计 {res['worker_seconds']:.3f}/1800 GPU-worker 秒，包含进程初始化、sanitizer 与 CPU 等待。100 W 与风扇/过温保护保留，全部 GPU 工作已结束，无后台运行队列。租赁费 0 元，电费未计量。旧原始数据与交付 ZIP 未修改；只清理了经 ZIP 哈希核验的临时重复解压目录。")
 add('\n完整包执行 `python3 src/recompute.py`，只需 NumPy，不依赖 CUDA/PyTorch，可重算每阶段选择、输入隔离、原始统计、正确性与源文件锁；ZIP 带 manifest，独立解压复算及 CRC/哈希 QA 另见交付索引。小包供网页版 GPT 审阅，缺少完整 raw/二进制，不能独立复算。')
 add('\n## 论文结论边界\n\n现阶段可复用的是明确有净收益的 GQA kernel 实现，以及“调度开销/访存实现足以压过微小地址亲和”的对照证据。不能写成已经证明 GPU 物理 NUMA、地址调度带来本文全部加速，或提出新的向量化算法。仍需真实模型接入、成熟专用 decode 基线和其他硬件复验，才能讨论系统级收益与论文新颖性。')
 (ROOT/'reports/REPORT.md').write_text('\n'.join(lines)+'\n');print('REPORT_PASS')
if __name__=='__main__':main()
