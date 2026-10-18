"""Generate reviewable research reports from completed paired measurements."""
import collections,csv,json,math,pathlib

ROOT=pathlib.Path(__file__).resolve().parents[1];DATA=ROOT/'derived/implementation_v1';OUT=ROOT/'implementation/reports'
def load(name):return json.loads((DATA/name).read_text())
def write(name,text):(OUT/name).write_text(text.rstrip()+'\n')
def ratio(d):return f"{d['time_ratio']:.4f} [{d['ratio_interval'][0]:.4f}, {d['ratio_interval'][1]:.4f}]"
def main():
 s=load('summary.json');assert s['method_campaign_complete'];cases=load('case_results.json');p=load('packet_applicability.json');freeze=s['freeze']
 agg=s['aggregate'];layer=agg['moe_layer'];group=agg['grouped'];drift=load('anchor_sensitivity.json');census=load('graph_census.json')
 # Names are conservative scope labels, not an assertion of publication novelty.
 if freeze['full_q']==1:
  state='SAME_CORE_GAIN_ONLY' if group['FULL_over_SIMPLE']['ratio_interval'][1]<1 else 'NO_INCREMENT_IN_SCOPE'
 elif group['FULL_over_SIMPLE']['ratio_interval'][1]<1 and layer['FULL_over_SIMPLE']['ratio_interval'][1]<1 and layer['FULL_over_LIB']['ratio_interval'][1]<1:
  state='OPERATOR_METHOD_OPPORTUNITY'
 elif group['FULL_over_SIMPLE']['ratio_interval'][1]<1:
  state='SAME_CORE_GAIN_ONLY'
 else:state='NO_INCREMENT_IN_SCOPE'
 s['research_status']=state;s['backbone_status']='MATH_BACKBONE_GAP' if freeze['math_backbone_gap'] else 'NO_PREDEFINED_BACKBONE_GAP'
 s['selection_status']='DEGENERATE_Q1_FULL_ALIASES_ABL' if freeze['full_q']==1 else 'NONTRIVIAL_QCAP_SELECTED'
 s['new_information_increment']='NOT_IDENTIFIED_FULL_ALIASES_ABL' if freeze['full_q']==1 else 'SEE_PAIRED_ABLATION_AND_SCOPE'
 (DATA/'summary.json').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n')
 lines=['# T10 算子内调度与融合：续实验最终报告','',f"状态：`{state}`；主体状态：`{s['backbone_status']}`。资源阻塞已解除，候选已实现，预登记条件分支已完成。",'',
  '这次已经真正运行算子内 CORE/BAL/CACHE/FULL/ABL 与四格融合，而非仅测原生库。结果只适用于本机 T10、100 W 上限、当前两种 SM75 数学配方、合成固定描述符/固定 post-route 输入。物理 NUMA、动态路由、完整模型和跨平台泛化没有得到验证。','',
  f"主 grouped FULL/LIB 时间比为 **{ratio(group['FULL_over_LIB'])}**，FULL/同体强简单策略为 **{ratio(group['FULL_over_SIMPLE'])}**。完整 post-route 层 F1S1/LIB 为 **{ratio(layer['FULL_over_LIB'])}**，同融合 F1S1/F1S0 为 **{ratio(layer['FULL_over_SIMPLE'])}**。时间比小于 1 表示更快。",'',
  ('**选择退化：FULL 冻结为 qcap=1，正式测试没有多 tile packet，FULL 与 ABL 是完全相同的配置并去重。开发阶段确实运行了 q>1，但未被全局选中。正式 FULL 的同体正效应予以保留；它不能归因于自适应包长信息，新增包长规则的增量没有被识别。FULL/ABL 的 1.0 与零宽区间来自 alias，不是独立消融的统计证据。**' if freeze['full_q']==1 else 'FULL 冻结后 q>1 的实际覆盖见 packet 适用域表。'),'',
  '## 实际完成范围','',
  f"本轮完成 {s['case_blocks']} 个 case-block、{s['phases']} 个含锚 phase；其中独立测试/回归比较 {s['formal_test_case_blocks']} 个 case-block。每组六个独立进程及 payload/weight seed。层的 route 重复三组种子族，不能说有六套独立路由。原结构形状已在旧轮次出现，新输入不构成新结构外推。",'',
  f"开发集 24 个 grouped 形状 × 6 块，比较两种数学体、固定 CACHE q1/2/4、12 个 FULL 配方及两个已装 LIB。按开发数据冻结 recipe={freeze['recipe']}，CACHE q={freeze['cache_q']}，FULL qcap={freeze['full_q']}、waves={freeze['full_waves']}，simple={freeze['simple']}，LIB={freeze['library']}。完整层仅在六个开发层选择一次 LIB，最终为 {s['layer_freeze']['layer_library']}；调度参数不再调整。",'',
  f"开发 CORE/LIB 比值为 {freeze['core_over_library']:.4f}。预登记 engineering 阈值为 1.25；因此本次执行 {'固定 24 grouped + 12 dense + 6 异质 K 控制，以及固定 6 测试层' if freeze['math_backbone_gap'] else '全部原 grouped/层测试域及固定控制'}。这不是从测试收益选出来的子集，也不是方法 NO-GO 判据。两种固定数学配方已实际运行，没有为追平库继续改主循环或扩展配方。",'',
  '## 配对效应','',
  '| 范围 | FULL/LIB | FULL/冻结强简单策略 | CORE/LIB |',
  '|---|---:|---:|---:|']
 for suite,g in agg.items():lines.append(f"| {suite} | {ratio(g['FULL_over_LIB'])} | {ratio(g['FULL_over_SIMPLE'])} | {ratio(g['CORE_over_LIB']) if 'CORE_over_LIB' in g else '不适用'} |")
 lines += ['', '主比较为按 case 等权、先求每 process block 的平均 log ratio，再做 20,000 次固定种子 block bootstrap。两项主比较使用 97.5% 边际区间，Bonferroni 得到各 suite 内同时 95% 区间，控制 suite 也采用这个口径；不宣称所有表格和逐 case 同时覆盖。其余消融及逐 case 区间为探索性 95%。六块样本较少，bootstrap 不能消除时间趋势或同一路由族相关，六轮次序也不保证完全抵消位置和前序影响。', '',
  '![主要效应](../figures/primary_effects.png)','',
  '全部逐 case 正例、负例、原始六块绝对毫秒与区间见 `derived/implementation_v1/case_results.json`，没有删除慢 case。','',
  '逐 case 探索性 95% 区间中，24 个 grouped 有 1 个快于 LIB（grouped-079）、23 个慢；12 个 dense 控制有 1 个快（dense_control-020）、10 个慢、1 个跨 1；6 个异质 K 控制全部慢。六个层中 moe_layer-017 是局部正例（F1S1/LIB=0.6888），四个层慢于 LIB，moe_layer-009 的区间跨 1。逐 case 区间未做全表多重比较校正；这些正例也不证明 qcap=1 下的新信息增量。','',
  '## 四格归因与边界','',
  '| 比较 | 时间比及探索性 95% 区间 | 解释 |','|---|---:|---|',
  f"| F0S1/F0S0 | {ratio(layer['SCHEDULE_AT_F0'])} | 未加 sideband 时的调度净差 |",
  f"| F1S1/F0S1 | {ratio(layer['FUSION_AT_FULL'])} | FULL 中 producer sideband 的净差 |",
  f"| F1S0/F0S0 | {ratio(layer['FUSION_AT_SIMPLE'])} | simple 支付相同 sideband 成本 |",
  f"| (F1S1/F1S0)/(F0S1/F0S0) | {ratio(layer['FUSION_SCHEDULE_INTERACTION'])} | 融合与调度的乘性交互 |",'',
  '![四格绝对延迟](../figures/layer_four_cells.png)','',
  '新调度在 `src/packet_visitor.h::OpPacketVisitor`；数学体 `OpFusedGemmGrouped::operator()` 与上游逐字节一致。FULL 相比 CACHE 新增总 tile / worker waves 与 K 工作预算限制，BAL 是原 round-robin 及异质 K 的静态排序。同体间全输出逐位相同。q=1 仍可能改遍历顺序，不能把 q=1 的差异解释为多 tile 复用。', '',
  'F0/F1 使用相同有用 gather pack；F1 在其中额外产出两项总 tile sideband。FULL 的 F1 省去每 CTA 内重复总量规约。没有新增外置调度 kernel，没有热路径 scheduler D2H，没有按 expert CPU 发射，没有算子内部全设备等待。库自己的合法内部节点全部计入。', '',
  '固定 post-route 层包括 pack、两次 grouped GEMM、SiLU/multiply、unpack、gate multiply 和 reduce；每请求只有输出边界同步。描述符和 route/count 在热计时外准备，不包含 router/count/scan、动态输入 ring、冷权重换层或完整模型。没有可用成熟 attention 内部 adapter，因此本轮 attention 候选为 NA，旧 attention LIB 数据不冒充候选。', '',
  '内部 scheduler/mainloop/DRAM 成本没有被硬件计数器分离；只支持净时间和同体消融。相邻 tile 的 B 缓存复用是机制意图，未显式跨 tile 保留 fragment，也没有直接测得 L2 命中率变化。不能由本结果推导 SM 间延迟、NUMA 岛或物理亲和。', '',
  '## 正确性、运行条件与漂移','',
  f"正式全输出检查摘要 {s['numerical']['records']} 条，全部通过={s['numerical']['all_pass']}，最大 relative Frobenius={s['numerical']['max_relative_frobenius']:.8g}。同体 bitwise 失败 {len(s['same_body_bitwise_failures'])}，热身违反 {len(s['warmup_violations'])}，测量次数越界 {s['measurement_bounds']['repeat_violations']}。原容差为 abs<=.005+.005abs(ref)，relative Frobenius<=.002；资格包含空 expert、尾块、多 packet、65 experts、改输入及全输出 NaN 清除。",'',
  '有限 CUDA 12.8.93 memcheck 为 0 errors。前两次旧 sanitizer 分别因 injection library 与工具版本启动失败，原日志完整保留，不能算作候选数值或越界失败。最终六个数学 kernel 均含 HMMA 指令；实际二进制、源码哈希和只读执行快照清单可追踪。', '',
  f"遥测共 {s['thermal']['samples']} 个约 1 Hz 样本，power limit 集合={s['thermal']['power_limits_w']} W，温度范围={s['thermal']['temperature_range_c']} °C，SM 时钟范围={s['thermal']['sm_clock_range_mhz']} MHz。包含初始化/空闲样本，不能把最低频率当作每个正式 phase 的频率。保留原风扇、过温、低转速与 watchdog 保护；100 W 不是锁频。",'',
  f"首尾锚差超过 5% 的 case-block 为 {s['drift_over5_count']}/{s['drift_rows']}，全部保留。算子 aggregate 50–200 ms 目标外的 phase 为 {s['measurement_bounds']['operator_aggregate_outside_50_200_ms']}；重复数仍固定在 128–512 边界。CUDA event 测到的是时间跨度，不是硬件 busy time；层为 128 次真实逐请求 ready 测量，不由均值推 p99。",'',
  '首尾锚敏感性：','', '| 范围 | 平衡序列内 LIB | 首锚 LIB | 尾锚 LIB | 点估计方向是否变化 |','|---|---:|---:|---:|---|']
 for suite in agg:
  rows=[d for d in drift if d['suite']==suite]
  vals=[math.exp(sum(math.log(d[k]) for d in rows)/len(rows)) for k in ['primary_ratio','head_ratio','tail_ratio']]
  flip=min(vals)<1<max(vals)
  lines.append(f"| {suite} | {vals[0]:.4f} | {vals[1]:.4f} | {vals[2]:.4f} | {'是，DRIFT_LIMITED' if flip else '否；仍不能排除策略相关频率/顺序影响'} |")
 lines += ['',f"层 route-family 敏感性（仅 3 个单位）：F1S1/LIB {ratio(s['layer_route_family_sensitivity']['FULL_over_LIB'])}；F1S1/F1S0 {ratio(s['layer_route_family_sensitivity']['FULL_over_SIMPLE'])}。这里只是保守分组敏感性，不增加样本量。",'',
  f"内存余量不合格：算子 {len(s['memory']['operator_margin_failures'])} 项，层 {len(s['memory']['layer_margin_failures'])} 项。算子峰值包括 FP64/逐位验证存储；层在释放大中间参考后计峰值，但仍持有最终 reference、exact output 和所有共用输入的 Graph，不冒称某一策略独占生产峰值。每 case 原峰值与 margin 状态在 raw。",'',
  '## 初始化、预算与交付','',
  'AOT 编译在 CPU 完成，三次构建日志（含一次 link 参数修复）留存。正式测量不重新编译。weights/data 创建、FP64 reference、静态 descriptor、Graph capture 和 pilot 不进入 steady latency；其合计残差在 `COST_ACCOUNTING.csv`，不能当作部署初始化成本。未分别计时各项启动成本，冷启动/回本次数为未建立，不画虚假交点。', '',
  f"原 16 worker 小时累计使用 **{s['budget']['all_campaign_used_seconds']/3600:.4f} 小时**，本轮新增 **{s['budget']['implementation_used_seconds']/3600:.4f} 小时**，剩余 **{(57600-s['budget']['all_campaign_used_seconds'])/3600:.4f} 小时**。预算包含获锁后准备与运行，旧 62 条记录未清零；CPU 源码实现时间与 worker 时间分开。全部本地运行，未购买算力。",'',
  '轻量包包含全部本轮原始 case/phase 数据、失败日志、遥测、Graph census、源码、实际二进制、去重的执行快照及复算脚本；不含旧轮全部 raw、重复 vendor checkout、工具链、权重和激活。`PACKAGE_SCOPE.json` 和 SHA 清单说明边界。旧报告和旧包仍保留。', '',
  '本轮已完成可支持的候选实验；没有保证论文创新性或可发表性。后续首先要解决主体相对库的差距、候选相对固定 CACHE 的真实增量、q 退化域及动态生产路径，而不是把已有库结果或遍历顺序收益改名成物理 NUMA 优化。']
 write('OPERATOR_FUSED_IMPLEMENTATION_REPORT_t10.md','\n'.join(lines))

 lines=['# Packet 适用域：实测资源和原规则','', '所有数字来自实际 adapter 的资源元数据与 GPU 已执行 shape。CPU 重建逐条校验 raw 中 packet 数与长度分布，未改变原 work_budget=128。','',
  '| recipe | block tile | threads | CORE/CACHE/FULL registers | shared bytes | 公共 worker 容量 |','|---|---|---:|---|---:|---:|']
 resources=load('actual_resources.json')
 for r in [0,1]:
  rr=[resources[f'recipe{r}_mode{x}'] for x in range(3)];a=rr[0]
  lines.append(f"| {r} | {a['tile_m']}×128×32 | {a['threads']} | {'/'.join(str(x['registers_per_thread']) for x in rr)} | {a['shared_bytes']} | {min(x['active_blocks_per_sm'] for x in rr)*a['sms']} |")
 lines += ['', '实际 worker=min(输出 tiles, 上表容量)，至少 1；无 SM 绑定。q=1 在 Mtiles>1 且 Ntiles>1 时也可改变 native 顺序。32 个原 K=4096 grouped 计划因 Ktiles=128，预算项限制 q<=1；它们是多 tile 复用负控制。', '',
  '| 开发 case | recipe | tiles | workers | qcap4/w1 的 q | packets | 尾包 | q>1 tiles |','|---|---:|---:|---:|---|---:|---:|---:|']
 for x in p:
  if x['cohort']=='implementation_calibration' and x['block']==0 and x['mode']==2 and x['q_cap']==4 and x['waves']==1:
   lines.append(f"| {x['case_id']} | {x['recipe']} | {x['tiles']} | {x['workers']} | {sorted(set(x['q_per_nonempty_problem']))} | {x['packets']} | {x['tail_packets']} | {x['multitile_tiles']} |")
 lines += ['',f"正式冻结 recipe={freeze['recipe']}、qcap={freeze['full_q']}、waves={freeze['full_waves']}。以下按实际使用的 FULL 包统计，q>1 case-block 计数不会把未选择的开发配方冒充正式效果。",'',
 '| 阶段/部件 | 记录数 | 有 q>1 记录 | q>1 tile / 全 tiles |','|---|---:|---:|---:|']
 by=collections.defaultdict(list)
 for x in p:
  if x['variant'] in ('FULL','F0S1','F1S1'):by[x['cohort'],x['variant'],x['component']].append(x)
 for key,rows in sorted(by.items()):lines.append(f"| {' / '.join(key)} | {len(rows)} | {sum(x['has_q_gt1'] for x in rows)} | {sum(x['multitile_tiles'] for x in rows)} / {sum(x['tiles'] for x in rows)} |")
 lines += ['', '完整原始分布含每个非空 problem 的 q、packet length、tail packet 数，见 `packet_applicability.json`。这是调度工作分配计数，不是硬件实际尾部时延或 DRAM 流量。']
 write('PACKET_APPLICABILITY.md','\n'.join(lines))

 lines=['# 实际 Graph DAG 与 launch/transfer 账本','',
  '数据来自捕获后的 CUDA Graph 只读遍历，未消耗额外 profiler trace 预算。它证明图内节点类型和 kernel 符号；不是硬件逐次 trace。源码核查补充 host 等待/描述符传输口径。','',
  '算子 CORE/BAL/CACHE/FULL/ABL → 一个 grouped GEMM kernel。CACHE/FULL 的调度在该 kernel 的 visitor 内。资格用 `count_visits` 不进入正式图。','',
  '全层四格 → gather pack（F1 含 sideband）→ grouped up → SiLU → multiply → grouped down → unpack → gate multiply → reduce。F0 与 F1 只有 pack 内 sideband 路径不同。库侧完整保留内部 split-K/merge 与必要节点。','',
  '| 阶段 | 策略 | 实际 kernel 节点数集合 | 图内 memcpy 节点数集合 |','|---|---|---|---|']
 by=collections.defaultdict(list)
 for g in census:
  if '_test' in g['cohort']:by[g['cohort'],g['variant']].append(g)
 for key,rows in sorted(by.items()):lines.append(f"| {key[0]} | {key[1]} | {sorted({r['kernel_nodes'] for r in rows})} | {sorted({r['node_types'].get('1',0) for r in rows})} |")
 lines += ['', '别名策略复用相同一次测量和同一 Graph，不另造节点。候选没有额外 plan launch、热路径 scheduler D2H 或算子内 host wait。每个 grouped 静态描述符为 problem shapes 12E 字节 + 三个指针及三个 stride 数组 48E 字节，共 60E；全层两个 GEMM 分别持有。该 H2D 构造在初始化而非每步。F1 每步写两个 int32（8 字节），在有用 pack 中产生。', '',
  '单算子一批 replay 末端一次同步；全层每请求输出边界一次同步。GPU 数值校验、资格计数及 sideband 校验可同步/D2H，均在性能计时外。完整逐 case 账本见 `LAUNCH_AND_TRANSFER_LEDGER.csv`；kernel 名称树见 raw，census 含计数。节点少不保证速度快。']
 write('KERNEL_DAG_BEFORE_AFTER.md','\n'.join(lines))
 print('REPORTS_COMPLETE',state)

if __name__=='__main__':main()
