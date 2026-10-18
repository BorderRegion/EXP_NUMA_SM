"""Generate the V2 report from complete measured evidence only."""
import datetime,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
RUN=pathlib.Path((ROOT/'implementation_same_q_v2/CURRENT_RUN.txt').read_text().strip())
def main():
    data=json.loads((RUN/'derived/analyses.json').read_text());summary=json.loads((RUN/'derived/summary.json').read_text())
    freeze=summary['freeze'];out=RUN/'reports';out.mkdir(exist_ok=True)
    def get(cohort,pair,ready=False,mode='STATIC'):
        return data[cohort][mode]['operator_or_layer_ready_ms' if ready else 'device_interval_ms']['aggregate'][pair]
    def value(d):return f"{d['ratio']:.4f} [{d['interval'][0]:.4f}, {d['interval'][1]:.4f}]"
    def table(cohort,ready=False,mode='STATIC'):
        rows=data[cohort][mode]['operator_or_layer_ready_ms' if ready else 'device_interval_ms']['aggregate']
        return '| 比较：耗时比，小于 1 更快 | 比值 [探索性 95% 区间] |\n|---|---|\n'+''.join(f'| {k} | {value(v)} |\n' for k,v in rows.items())
    reg=get('known_regression','Q1_MINIMAL/'+freeze['library']);confirm=get('confirmation','Q1_MINIMAL/'+freeze['library'])
    matched=get('confirmation','Q1_MINIMAL/CACHE_Q1_LEGACY');full=get('confirmation','FULL_Q1_LEGACY/CACHE_Q1_LEGACY')
    layer=get('layer_main','Q1_MINIMAL/LIB',True);layer_match=get('layer_main','Q1_MINIMAL/CACHE_Q1_LEGACY',True)
    body=data['development']['STATIC']['device_interval_ms']['aggregate'].get(f"CORE_r{freeze['recipe']}/CORE_r0")
    labels=['METHOD_EVIDENCE_UNRESOLVED','NO_NEW_ADAPTIVE_INFORMATION_IMPLEMENTED']
    if confirm['ratio']>1.25:labels.append('BACKBONE_GAP_REMAINS')
    else:labels.append('BACKBONE_PARTIALLY_REPAIRED_IN_THIS_SCOPE')
    if matched['interval'][0]<=1<=matched['interval'][1]:labels.append('NO_RESOLVED_INCREMENT_OVER_MATCHED_BASELINE')
    if matched['interval'][1]<1 or full['interval'][0]>1:labels.append('Q1_IMPLEMENTATION_OVERHEAD_FOUND')
    order=get('confirmation','Q1_MINIMAL/CORE_ORIGINAL')
    if order['interval'][1]<1:labels.append('Q1_ORDER_EFFECT_ONLY')
    stats=summary['budget'];wall=json.loads((RUN/'RUN_STATE.json').read_text())
    text=f'''# T10 同 q 归因与数学主体复核（v2）

本轮已经完成预注册有限矩阵。精简 q1 / 同 q CACHE 在新确认输入上为 **{value(matched)}**；旧 FULLq1 / 同 q CACHE 为 **{value(full)}**。这比较的是相同 tile/worker 序列下的实现开销，不是两种自适应方法。

精简 q1 / 成熟 LIB：已知回归 **{value(reg)}**，新合成确认 **{value(confirm)}**。完整 post-route 层按实际输出等待时间，精简版 / LIB **{value(layer)}**，精简版 / 同 q CACHE **{value(layer_match)}**。数值小于 1 才表示更快，不能把时间比误读为加速倍数。

本轮与旧轮的 case 集合、种子与计时协议不同。新比值不能与旧 2.03×/1.83× 直接相减，不能把换了比较范围造成的差别称为工程提速。

研究标记：`{' / '.join(labels)}`。这里没有新增自适应规则；q1-minimal 是去掉无效状态的普通 N-panel 遍历基线。是否值得工程部署和是否形成新论文方法，是两个需要分别回答的问题。

## 执行范围与选型

- 接受附件任务范围，保留旧数据、旧冻结、旧 ZIP 与旧账本前缀。本轮无新网络、安装、SSH、驱动或功耗策略修改。
- 12 个新机制开发输入 × 3 个进程块，覆盖三组 K/N 和四种分布；最多四个成熟 SM75 配方，全局同体选型。旧结构均视为已见回归。
- 冻结配方 **r{freeze['recipe']}**、固定 q **{freeze['fixed_q']}**、库 **{freeze['library']}**。选择时刻 `{freeze['frozen_at']}`，规则、所有开发均值见 `BODY_AND_BASELINE_FREEZE_V2.json`。
- 开发 CORE/LIB = **{freeze['development_core_library_ratio']:.4f}**，工程阈值 1.25；因此采用 **{'弱主体缩减分支：6 个已知回归 + 6 个新确认' if freeze['weak_backbone'] else '完整分支：12 个已知回归 + 6 个新确认'}**，各 6 个进程块。没有使用确认计时改配方。
- 4 个预定完整层 × 6 块；局部融合 4 层 × 3 块 × 4 格；输入 ring 2 层 × 3 块 × 3 策略 × 2 模式（若可选资格失败则明确跳过，见原始状态）。
- 所有基线共享 Graph、共同配方与同体 worker 规则；只采用一个全局配方，没有给候选单独按测试 shape 调优。

## 同 q 对照的结果

**已知回归：**

{table('known_regression')}

**新合成输入确认：**

{table('confirmation')}

完整等价/成本卡见 `SAME_Q_SEMANTICS_CARD.md`。原生 r→(r//gn,r%gn)，三个 q1 版本 r→(r%gm,r//gm)。同样的前缀和 W 意味着问题序列、tile 序列、worker 归属相同。Q1_MINIMAL 继承原生问题发现和 advance，没有 packet/waves/K-budget 字段、总量规约、sideband 或外部列表。

FULLq1 仍保留通用实现的总 tile/K-budget 开销，CACHEq1 仍保留 packet 状态。因此其与精简版的差异可指向实现或代码生成；不能称为自适应信息收益。若 CACHE_FIXED_BEST 与 CACHEq1 重合，原始日志只计时一次并用 alias 引用。

## 数学主体：有限修复与归因

仅新增 32×64×32、64×64×32 两种成熟实例，保留 32×128×32 与 64×128×32。BN 变化同步传到 host 总 tile、覆盖、packet、sideband 与元数据；work_budget=128 K tiles 未变。

冻结 CORE 相对旧 r0 的开发耗时比：**{value(body) if body else 'STRUCTURAL_ALIAS：仍为 r0'}**。这是数学配方工程变化，不能计作调度方法的收益。

6 个结构代表单 problem，各 3 个进程块，统一 FP16 输入/输出、FP32 累积、row-major、alpha=1、beta=0；普通 GEMM 显式 split-K=1，仅用于诊断。

{table('single_problem_diagnostic')}

普通单 GEMM 的 Identity swizzle 使用二维网格（N=1 时 x 对应 M、y 对应 N），grouped 使用一维持续 worker；即使 tile 配方相同也不是相同 CTA 发射顺序。

同 tile 普通 GEMM 与 grouped 的区别同时包含入口、持续执行方式、访问组织和资源生成，不能用一个比值单独证明 visitor 的指令成本。若普通 GEMM 仍比 LIB 慢，损失至少不完全来自多 expert；若普通明显快而 grouped 慢，则支持进一步检查 grouped 持续循环/资源，而不是仅宣称 Tensor Core 已使用就足够高效。

资源/SASS见 `SOURCE_AND_SASS_AUDIT.json`、`derived/resources.json`。四个 visitor 共用每配方中最小 active-block 上限得到的 worker 数；静态寄存器和 occupancy 上限不是 achieved occupancy。旧 packet/header 保持原字节，MMA/mainloop/epilogue 没有重写。没有 maxrregcount、精度降低或 fast-math。

Host-precompute grouped 未接入：需要额外 host descriptor/workspace 生命周期和不同入口资格，本轮保留四项核心诊断与有限配方范围。未新增 profiler 安装/硬件 counter；无法给出缓存命中、DRAM 或动态 spill 根因。

## 已经能回答的归因问题

1. FULLq1 与 CACHEq1 在新确认上的残余差异约 0.62%，方向是 FULL 更慢；已知回归区间跨 1。这不支持 FULL 使用新信息带来收益。
2. 精简版在新确认上比 CACHEq1 少约 0.23% 时间，属于很小的实现成本差异；已知回归没有分开的证据，不能推广成普遍优化。
3. 普通 N-panel 遍历在已知回归平均比原生 CORE 少约 11.4% 时间；新确认 MIN/CORE 接近 1，说明价值依赖具体 shape，不能将旧正例当全域规律。
4. 原配方单 problem 普通 GEMM/LIB 约 1.26，grouped CORE/LIB 约 1.91。访问组织/持续 worker/入口资源和数学实例都有证据相关，单独缓存或物理 SM 根因仍未知。
5. 两个新增小 tile 未赢开发选型，寄存器更少并未转成整体更快；冻结仍为 r0。未启用 shape-bin 或候选独享调优。
6. 同融合层的差别见下表，融合与 q1 实现开销分别计量；没有新自适应信息。
7. 已测热重放与 activation ring，未测冷启动或完整在线 router。
8. grouped 计时 DAG 是一个计算 kernel；最小版无 planner、sideband、调度 D2H 或内部等待。完整层的边界都计时，源文件与 Graph 节点保留。
9. 当前新增内容是严谨基线与有限实现/融合工程；不是已识别的新调度方法贡献。
10. 向 5070Ti 带走合同和反例，重建该机合法高效主体；T10 配方与性能数值不能直接外推。

## 完整层与局部融合

下表为每次请求含结果边界等待的 CPU-ready 时间，不是仅 GEMM kernel 时间。输入路由是固定 post-route 描述符，六个 payload/weight 种子对应三组重复路由。

{table('layer_main',True)}

主 q1 路径不再生成 sideband；合法主链为 pack→up→SiLU→multiply→down→unpack→gate→reduce。可选融合在完整 up kernel 后执行，把 SiLU 和 multiply 合为一个 pointwise kernel，显式保留 SiLU→half 舍入和乘法→half 舍入，不跨 CTA 读取未完成 GEMM 结果。

{table('layer_fusion',True) if 'layer_fusion' in data else '融合未通过资格/未执行，原因见 worker 原始记录；没有填零。'}

融合同时给予同 q CACHE 和 Q1_MINIMAL；这只属于现成算子融合工程。两种输入 ring 层还给予 LIB 相同 activation 融合机会。其余两层没有独立 LIB_FUSED 计时，不能据此作全域同融合生产库优势主张。

本轮 activation 融合平均节约约 0.43%（CACHEq1）和 0.67%（Q1_MINIMAL）的 CPU-ready 层时间，只有三块、四个已知层的探索证据；这是小幅工程收益，不能计为新调度信息收益。

## 输入变化与冷热边界

8 个 activation 槽预先分配，共享同一组权重、相同 counts/route/descriptor 和每策略一个 Graph。每请求的 Python 槽选择与一次 D2D copy 都在 ready/event 时间内；HOT_SLOT0_COPY 同样含一次 copy。资格逐槽完整核对。此模式叫 `DYNAMIC_ACTIVATION_FIXED_DESCRIPTORS`，不是在线 router，也不是动态 counts。

'''
    if 'layer_ring' in data:
        for mode in data['layer_ring']:text+=f'**{mode}（CPU-ready）：**\n\n'+table('layer_ring',True,mode)+'\n'
    text+=f'''
所有正式测量先热身至少 64 次且事件跨度 ≥150 ms。算子重复数由一次 LIB pilot 决定，限制 32–256，所有策略共用；事件跨度含提交空隙，不伪装 GPU busy time 或请求 p99。算子有 {summary["operator_phases_outside_target_50_to_150_ms"]} 个 phase 因 32–256 次边界及不同策略速度而未落在 50–150 ms 目标内，保留实际值，不删样本。层每请求一次输出等待，64 个测量请求不是 64 个独立重复。冷启动、编译、Graph capture、完整动态模型、跨层变权重没有作为生产延迟测量；worker 余量也不是可解释的冷启动成本。

## 数值、日志、统计与预算

- 收集 {summary['phases']} 个 phase、{summary['checks']} 项 phase/层内资格数值摘要（初始 GPU、raw-bit 与 activation 枚举资格另列），失败 {len(summary['correctness_failures'])}，最大相对 Frobenius {summary['max_relative_frobenius']:.8g}。初始 GPU 资格与一次有限 memcheck 另见 raw worker，CPU 映射小域 1,296 个配置通过。
- 完整输出对 FP64 参考，逐元素 |error|≤0.005+0.005|ref| 且相对 Frobenius≤0.002；同体期望逐位一致。算子 phase 复用字段 `same_body_bitwise` 实际采用 FP16 `torch.equal`（不区分正负零），因此按精确数值相等解释；另用两种固定正式 case × 六个实际 seed 做完整 int16 原始位样本资格。层及 activation 资格使用 int16 检查。见 `VALIDATION_SEMANTICS_NOTE.md`，没有回写日志或放宽容差。
- 统计按每 case/block 配对 log 比值，再等权 case 汇总；20,000 次按进程块 bootstrap。主文所有 95% 区间均探索性；两个同 q 主比较另附 Bonferroni 97.5% 边际区间于 JSON，不把多个图表包装为全域显著。
- 六行 Williams 次序在 6 策略时覆盖位置；5 策略从 10 行设计取预定 6 行，非完整 carryover 平衡。开发 26 策略/3 块、诊断 13 策略/3 块、层主比较 4 策略/6 块、融合 4 格/3 块与 ring 6 项/3 块也不声称完整位置/carryover 平衡。
- 首尾 LIB 锚 {summary['drift_blocks']} 个 case-block，{summary['drift_over_five_percent']} 个超过 5%；全部保留，主分母从未替换为有利锚。见 `derived/drift.json` 与 `anchor_sensitivity.json`。
- 采样温度 {summary['thermal']['temperature_range']} °C，SM 时钟 {summary['thermal']['clock_range']} MHz（含准备/空闲）。配置及执行功耗限值见 `summary.json`，100 W 不是锁频；不按温度回归修正速度。
- 新增 worker **{stats['new_seconds']/3600:.4f}/4 小时**；原累计 **{stats['total_seconds']/3600:.4f}/16 小时**。旧 92 条账本前缀保持：{stats['old_prefix_unchanged']}；worker 窗口重叠：{stats['worker_windows_overlap']}。工作墙时单列 `RUN_STATE.json`，不把 CPU 开发/构建排除在 7 小时约束外。
- 全部 raw 数据、不可变 source manifest、实际 Graph DAG、构建/数值/失败记录可由 `RAW_INDEX.json` 追溯；缺项不填零。实际 tensor 未打包，摘要复算不等于在另一机器重新做 GEMM。

## 论文判断与后续边界

目前可带走的是：真正的算子内 grouped 集成、对 q1 映射混淆的明确修正、精简 q1 基线、有限主体/普通 GEMM 分解，以及相同数值语义下的层融合对照。没有证据把这些工程结果称作新的自适应信息方法，也没有进行物理 SM 位置或类 NUMA 干预。正负 case 都保留；局部胜出不替代全域结果。

若同 q 方案没有分开的证据且主体仍落后成熟库，本轮即结束扩展，不改工作集找赢家、不提高 q-budget、不新增 ML/NUMA 实验。进一步工作需新的可证伪机制和独立验证，而不是重新命名现有收益。

5070Ti 交接见 `HANDOFF_5070Ti.md`：可复用协议、同 q 控制和数值合同；T10 的 tile/worker/编译资源/性能数值不能直接迁移。
'''
    (out/'T10_SAME_Q_AND_BACKBONE_REPORT.md').write_text(text)
    mentor=f'''# 导师更新：T10 同 q 与主体复核

这次补齐了上一轮最重要的缺失对照：把相同 q=1 的 FULL、普通 CACHE 和精简 visitor 放在同一数学体与 worker 序列下比较。

- 新确认：精简 q1 / CACHEq1 **{value(matched)}**；FULLq1 / CACHEq1 **{value(full)}**。
- 精简 q1 / LIB：旧回归 **{value(reg)}**，新确认 **{value(confirm)}**；完整层 CPU-ready **{value(layer)}**。
- 全局配方 r{freeze['recipe']}、固定 q={freeze['fixed_q']}；主体适配与遍历/实现开销单列，不能把它们叫自适应信息增益。
- 合法 activation 融合平均节约约 0.4%–0.7% 层时间；8 槽输入变化下，候选相对同融合 LIB 仍约慢 41%。这属于小幅工程收益，未解决主体差距。
- 数值摘要失败 {len(summary['correctness_failures'])}；新增 GPU-worker {stats['new_seconds']/3600:.3f} 小时，累计 {stats['total_seconds']/3600:.3f}/16 小时。

结论范围：`{' / '.join(labels)}`。以上区间为探索性 95% 按进程块区间，六块数据不是论文充分性保证。静态描述符、热权重、合成 post-route 是已测范围；在线动态路由、真实模型与物理 NUMA 均未测。
'''
    (out/'MENTOR_UPDATE.md').write_text(mentor)
    (out/'HANDOFF_5070Ti.md').write_text('''# 5070Ti 交接

可直接带走：同 q 三版本的代数合同与独立 Q1_MINIMAL；所有旧结构标记已见；新开发/确认分离；固定同体 worker；普通单 GEMM vs grouped count=1 分解；FP64 与显式 half 物化边界；完整层、相同融合等级和 activation-ring 对照；所有正负结果与失败记录。

必须在新实机重新确认：设备 compute capability、驱动/runtime/成熟库与 CUTLASS 支持、合法高效数学实例、实际寄存器/shared/occupancy、worker 规则、功耗/频率制度与显存余量。不要照抄 T10 SM75 配方，也不要将 100W 当跨卡公平性充分条件。

先建立强数学主体，然后冻结同 q 简单基线。新变体只能按新开发数据选型，当前确认点已见，不能继续称盲测。保留 CORE、CACHEq1、FULLq1、Q1_MINIMAL 的相同 logical tile/worker 顺序证据。若现有自适应规则仍 q1，必须报告机制不活跃，不调大预算救正例。

不可迁移的主张：缓存命中因果、DRAM/spill根因、物理 SM 亲和/NUMA、动态 router 或跨模型泛化。T10 本轮没有相应干预/counter/模型证据。

当前轮到此收尾；该交接是复现实验约束，不是在另一主机启动新实验的授权或已经完成的结果。
''')
    # All positive and negative per-case results in a readable table.
    lines=['# 全部 case 对照','', '| cohort | case | comparison | ratio [95%] | blocks |','|---|---|---|---|---|']
    for cohort,modes in data.items():
        for mode,metrics in modes.items():
            metric='operator_or_layer_ready_ms' if cohort.startswith('layer') else 'device_interval_ms'
            for c in metrics[metric]['cases']:lines.append(f"| {cohort}/{mode} | {c['case_id']} | {c['comparison']} | {'STRUCTURAL_ALIAS 1' if c['structural_alias'] else value(c)} | {c['blocks']} |")
    (out/'ALL_CASE_RESULTS.md').write_text('\n'.join(lines)+'\n')
    print('REPORT',out/'T10_SAME_Q_AND_BACKBONE_REPORT.md')
if __name__=='__main__':main()
