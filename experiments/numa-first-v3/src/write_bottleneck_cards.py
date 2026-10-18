"""Evidence cards from every native case, retaining unknown mechanism fields."""
import json
from common import *
r=runroot();d=json.loads((r/'derived/NATIVE_ANALYSIS.json').read_text());lines=['# 三族原生负载瓶颈卡','',f'生成时间：{utc()}。数值来自当前已完成块；最终状态见主报告。','',
'这些卡区分直接测量、结构代理和未知项。张量字节不是 DRAM 流量，虚拟页不是物理 home，Graph 节点数不是性能结论。应用分配内尚未验证短公式地址亲和，因此应用 M/T/X/Y/P 与融合×映射为 NA；不能把探针规则套到这些分配。','',
'时间单位均为毫秒。ready 是提交至输出可用，total-ready 再加显式缓存准备；batch 是紧密吞吐组均摊，不能用作请求 p99。区间按独立整块重采样；每帧不是独立重复。','']
def fmt(x):
 if x is None:return 'NA'
 return f"{x['estimate']:.6g} [{x['ci95'][0]:.6g}, {x['ci95'][1]:.6g}] (n={x['independent_blocks']})"
for case,card in sorted(d['cards'].items()):
 family=card['family'];rows=[x for x in d['summary'] if x['case']==case];stages={x['stage'] for x in rows};stage='P4' if 'P4' in stages else 'P2';rows=[x for x in rows if x['stage']==stage]
 lines += [f'## {case}','',f'统计阶段：{stage}。','']
 if family=='render':
  s=card['summary'];t=card.get('tile_access',{});api=card.get('api_trace',{})
  lines += [f"- 来源：本地已训练 3DGS，原生 renderCUDA 数学体逐字审计；{s['gaussians']:,} Gaussians，{s['width']}×{s['height']}，相机序列 {s['sequence']}。未训练或下载模型。",
   '- 工作单位：16×16 pixel tile，原始 Gaussian ID、每像素累积序列、alpha、阈值和 early-stop 不变。动态帧包含 preprocess/binning/sort；快照只测已有真实中间结果的 render。',
   f"- 内存：模型 {s['model_bytes']:,} B，geometry {s['geometry_bytes']:,} B，binning {s['binning_bytes']:,} B，image {s['image_bytes']:,} B，诊断 scratch {s['scratch_bytes']:,} B。这些是存储/容量，非消费流量。",
   f"- 候选列表结构：tile list 长度分位数 {t.get('list_length_quantiles','NA')}；颜色起始地址虚拟 4 KiB 页数分位数 {t.get('virtual_page_count_quantiles','NA')}；单页最大份额分位数 {t.get('majority_virtual_page_fraction_quantiles','NA')}。",
   f"- 实际调用：代表动态帧 {api.get('driver_kernel_calls','NA')} 个 driver kernel launch（与 runtime 计数重叠，不相加）；快照 Graph 一个 render kernel。动态路径有 CPU 可见的数量依赖，未做完整 Graph。",
   '- 机制判断：完整时间与快照差异显示上游不可免费忽略；候选列表跨很多虚拟页，且未展开12-byte跨页属性、未跟踪early-stop/条件加载；不能称实际消费页数。任意 tile 静态单域分配需要额外验证，但不能据此认定跨物理 home。',
   '- 已知 home 覆盖 0；多 home 比例、DRAM/L2 命中、远端访问、带宽瓶颈均 UNKNOWN。非均匀亲和对本负载的收益未直接测试。',
   '- 正确性：原生同相机完整 color/final-T/n-contrib 原始位比较及代表输出；它检验确定性与重放，不是与独立 renderer 的图像质量等价证明。相机拆分存在已记录的 P2/P4 Bonsai q0 重叠。','']
 else:
  inv=card.get('actual_graph_inventory',{});nodes={k:dict(nodes=v['node_count'],kernels=v['kernel_count'],copies=v['memcpy_count']) for k,v in inv.items()}
  lines += [f"- 来源类型：`{card['source_type']}`。结构/权重与实际张量大小详见 `derived/NATIVE_ANALYSIS.json` 对应 card。",f"- 有效数学量：{card['effective_flops']:,} FLOP。实际 Graph 节点：`{json.dumps(nodes)}`。",'- 已知 home 覆盖 0。硬件流量、L2 命中、远端访问和 stall counter 均未获得；不能单凭工作集大小归因。']
  if family=='sparse':
   bytes_=card['matrix_bytes']+card['consumer_unique_indexed_x_bytes']+card['output_bytes'];ai=card['effective_flops']/bytes_
   lines += [f"- 实际输入：{card['rows']:,} 行，{card['nnz']:,} nnz，RHS={card['rhs']}；保留原 int32 CSR 索引及顺序，一般可复算 FP32 values，非全 1 特例。",
    f"- 消费唯一存储代理：CSR {card['matrix_bytes']:,} B，索引涉及 x {card['consumer_unique_indexed_x_bytes']:,} B，输出 {card['output_bytes']:,} B；FLOP/上述字节={ai:.4g}，这是结构比值，不是硬件算术强度实测。",
    f"- 行长分位数 {card['row_degree_quantiles']}；列重用分位数 {card['column_reuse_quantiles']}；抽样 {card['sampled_rows']} 行的 x 虚拟页跨度 {card['x_virtual_page_span_quantiles']}。",
    '- 基线：torch/cuSPARSE 真正 SpMV/SpMM，Graph 含相同动态 x D2D copy；CPU double CSR 参考检查所有输出。矩阵结构来自真实图，x/values 为机制输入，非完整图应用。',
    '- 干预目标：连续行拥有的 A/indices 与跨行共享的 x 必须分开；短公式能否保留 x 亲和未验证。低结构算术强度使其值得后续研究，不能就此宣称 memory-bound。']
  elif family=='inference_grouped':
   meta=card['q1_metadata'];ai=card['effective_flops']/(card['active_weight_tensor_bytes']+card['activation_bytes']+card['output_bytes'])
   lines += [f"- 形状 (M,N,K)：{meta['shapes']}；FP16，一般随机可复算数据；形状是机制配置，不是真实 LLM。",
    f"- 权重 resident {card['resident_weights_bytes']:,} B，实际非零 M 参与的权重 {card['active_weight_tensor_bytes']:,} B，activation {card['activation_bytes']:,} B，output {card['output_bytes']:,} B；数学量/唯一张量代理={ai:.4g} FLOP/B。",
    '- 基线：cuBLAS 与已有 CUTLASS Q1-minimal、同体 CORE；所有实现包括相同 activation D2D producer。Q1 是普通调度控制，不是本轮 NUMA 方法。',
    f"- Q1 实际资源：{meta['workers']} workers，{meta['total_tiles']} tiles；各 mode 寄存器 {[x['registers_per_thread'] for x in meta['resources']]}，shared {[x['shared_bytes'] for x in meta['resources']]} B。库与 Q1 的完整差距计入。",
    '- 干预目标：小 M 权重流量、中 M 权重复用、大 M 计算与偏斜尾部；这些都是冻结的筛查理由。只有一般性能时间，不能把某项瓶颈当作已确证。',
    '- 正确性：4 个输入槽的同体原始位比较，FP64 数学参考，FP16 atol/rtol 0.005、相对 Frobenius 0.002；零 M 权重存储与实际消费区别记录。']
  else:
   lines += [f"- 形状：长度 {card['lengths']}，Hq={card['q_heads']}，Hkv={card['kv_heads']}，d={card['head_dim']}；KV {card['kv_bytes']:,} B，唯一张量 {card['unique_tensor_bytes']:,} B。",
    '- 基线：torch 高效 CUTLASS attention；Graph 包含 GQA query packing、attention 和输出布局处理。保持 softmax 与全 KV 语义，非完整 token 模型请求。',
    '- 长序列、batch 和不等长 KV 是访存/负载平衡候选，短序列是开销较显著的对照；实际 DRAM/互连瓶颈未知。',
    '- 四个输入槽模拟不同请求，未声称真实 KV append、路由生成或线上模型更新；FP64 参考与 FP16 数值合同同 grouped。']
  lines += ['- 状态：HOT、四槽 RING、128 MiB SM 扫描干预。扫描不是硬件保证的 flush，其时间单列并计入 total-ready。初始化汇总含 CPU 参考和诊断，不能全部算部署成本。','']
 lines += ['| 状态 | 方法 | ready [95% CI] | total-ready [95% CI] | batch 均摊 [95% CI] |','|---|---|---:|---:|---:|']
 for x in sorted(rows,key=lambda x:(x['state'],x['method'])):lines.append(f"| {x['state']} | {x['method']} | {fmt(x['ready_ms'])} | {fmt(x['total_ready_ms'])} | {fmt(x['batch_ms'])} |")
 lines += ['', '不能作出的结论：此卡没有证明物理 NUMA，也没有证明 NUMA 优化对该应用有效或无效；原生结果不替代本轮经验映射的真实应用对照。','']
(ROOT/'BOTTLENECK_CARDS.md').write_text('\n'.join(lines).rstrip()+'\n')
print('bottleneck cards',len(d['cards']))
