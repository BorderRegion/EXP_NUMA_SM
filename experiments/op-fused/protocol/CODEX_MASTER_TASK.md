# Codex 主任务书：双平台算子内调度＋生产者协同融合

版本：2026-10-15 v1。工作代号 OP-FUSED，仅作目录标识，不是已确立的方法名或首创主张。

## 0. 必须准确执行的研究目标

用户要求：以发表 GPU infra 论文为目的，验证推理负载是否更适合低成本资源/复用感知调度；不能把研究实现为外部通用分区框架，不能因为引入大量小 kernel、CPU 往返和逐组同步而毁掉本可获得的收益。

**主实现位置：已有 grouped GEMM 的 problem/tile scheduler，以及已有 attention 的 request/head/segment scheduler。** 计算主体、Tensor Core mainloop、已成熟的软件流水保持。元数据若必须产生，优先接在已有路由/计数/打包/scan 的合法生产点；局部 activation 等接入合法 epilogue。需要全局完成关系的计算仍保留正确边界，不制造死锁 megakernel。

本轮已批准从“物理NUMA”收窄/分层到三种可检验主张：
- L0 算子内工作分解与低调度开销；
- L1 权重/KV 的逻辑复用、缓存工作集与尾部平衡；
- L2 芯片/位置资源信息的额外价值，仅实际可观察且有同机制消融时使用。

**不测得 L2，不阻塞 L0/L1，但不得把 L0/L1 收益称为 NUMA。** T10 裁剪比例不预测 5070 Ti 效果；也不承诺新卡更好。

## 1. 旧结果如何使用

旧 T10 数据：W1 的 E_FULL/N≈1.0903、M/R≈1.0012；ca-GrQc 的 E_FULL 比 cuSPARSE 快，但分区 M 反而慢。它们说明应分离计算主体、外部执行组织与新策略，而不是证明任何推理算子都不适合。旧源码存在输入完成等待、跨 context 启动/汇合；不复制这些生产路径。

只复用编译/版本记录、进程锁、计时统计和输入管理；旧渲染器、CSR测试、Green分区、地址热图、旧 M/R 计划均不进入本轮主实现。旧 raw 只读。具体旧证据和新查证来源见 docs/09；没有新实验结果预填到本包。

## 2. 研究问题

RQ1：在两平台实际可用的成熟推理后端里，算子时间、元数据准备、CPU提交、内存流量/计算/尾部分别占什么？
RQ2：复用成熟计算体以后，改变内部工作映射是否优于其 native scheduler、普通均衡和已有 cache-aware 分组？
RQ3：在已经采用相同合法融合和 CUDA Graph 的条件下，新增调度信息还有多少独立收益？
RQ4：生产者生成少量附属元数据，是否减少独立准备，同时不拖慢生产者或增加中间流量？
RQ5：在动态路由/动态序列长度下，计划更新、原有归并和输出交付计入后，完整层及可运行模型是否仍获益？
RQ6：效应是否与可测的 tile 数/worker 容量、复用、尾部相关？是否只是一般参数调优，而不是物理拓扑？
RQ7：两平台/留出形状/真实 trace 的适用边界、初次编译与准备摊销、负例是什么？

本轮一个新调度规则、一个主 GEMM adapter、一个 attention adapter。不要同时开发通用编译器、LLM agent、完整 megakernel、分布式通信或模型训练。

## 3. 首先落实的结构性要求

1. 每个 expert 的计算不得变成一个 CPU 发射；每个 tile 也不准单独 launch。优先一个 grouped GEMM 调用。
2. 正式方案不新建 Green Context，不逐组切换上下文；默认单 primary context，使用本来需要的 stream/event。
3. 新任务描述留在设备端；不为取得 M_e、seq_len、token count 调用 `.item()`、D2H、全设备同步。
4. 新调度元数据优先不增加独立 kernel；已有 router/count/scan/pack/epilogue 可合法承载才承载。
5. `CUDA Graph` 只降低提交成本，不视为已把 kernel 合并；节点和中间流量仍计数。
6. 不把“少一个 launch”当成最高目标；必要的全局 scan、partial-output merge、分层归约继续存在且全额计费。
7. 已实现的库融合不能为了制造优势而关闭。新增融合必须有同融合基线。
8. 同一个输出 tile 的数值累积顺序默认不变。首轮不新增 split-K，不改路由、不丢 token、不降低精度。
9. 允许使用后端已有的低成本设备内领取机制；不能为了“零原子”强迫会产生严重长尾的静态stride。
10. 未建立高效同体基线时，新手写普通乘加循环不得成为 Tensor Core 方法的代表。

## 4. 分层终点，必须推进到有解释力的范围

- L_OP：真实维度的独立 GEMM/attention，输入已在GPU；用于计算与调度机会。
- L_PAIR：真实生产者→消费算子，动态尺寸/元数据变化计时；防止把准备成本藏掉。
- L_LAYER：完整 MoE FFN 或 attention block，包括必要路由/打包/scan/activation/归并；精确标注是否包含router。
- L_MODEL：本地已有且能完整驻留的预训练模型，真实请求序列；没有资产就明确未运行，不能用随机小网络冒充。

即便算子增量不明显，已能运行的完整层仍执行预注册的小型确认，避免仅凭孤立 kernel 提前判死。没有可用 adapter/资产则报告缺项，不换成旧渲染负载。

## 5. E0–E7 连续流程

### E0 本机资产与接口（T10/5070Ti 各0.5 worker小时上限）
读当前 CUDA、架构、库版本、预训练模型/trace、本地 CUTLASS/FlashInfer/等效后端。只做一次增量盘点。
建立 `BACKEND_CARD.md` 和 `LOCAL_RESOURCE_GAPS.md`；确认真正被调用的 kernel，不以包名代替后端。检查构建/导入是否会隐含下载，离线禁用这些入口或使用本地缓存。
预注册样例、split、计时路径、数值标准、预算、候选与简单基线的等额调优范围。CPU生成器与计划检查器通过不代表GPU实现通过。

### E1 成熟基线和成本分解（1.5h / 2h）
运行开发集而非留出集。cuBLAS/cuBLASLt、已可用 grouped GEMM、FlashInfer或等效成熟attention，分别建 isolated 与完整层 native 基线。
先建异步、buffer复用、同条件Graph基线。baseline某功能没有支持则记录，不能故意让它频繁编译/同步。
保存 production DAG 与 launcher census。至少12个开发代表点采少量现有profiler或host wrapper事件；profiling独立，不以 profiler 数字作主收益。
判断所选可修改计算主体是否已经与合理库实现接近；若同体native持续慢>15%且覆盖一半开发点，允许最多4次有依据的主体/参数适配。仍弱则标 `MATH_BACKBONE_GAP`，继续有限同体因果结果，不把弱主体负结果写成方法普遍失败。

### E2 单一候选与合法fusion落地（2h / 3h）
先做docs/02的完整tile覆盖与内核内映射，再做docs/03的producer/epilogue接入。
**不允许在这一阶段停留于“外面新加planner kernel”的最终架构。** 若临时实现需要单独准备，只能作诊断，随后要迁移或记 `UNFUSED_PROTOTYPE_ONLY`。不要将未完成承载方式的负结果直接判科研NO-GO。
每个局部元数据与fusion写一个短依赖说明，使用现有测试和有限sanitizer；不开发新的泛化证据框架。
参数只有 q_cap∈{1,2,4}、target_waves∈{1,2}，另有至多2个既有合法tile配方。总候选配方≤12；简单均衡/复用基线获得相同上限与数据。最终冻结。

### E3 算子独立验证（4h / 6h）
按docs/05/06完成 grouped GEMM 主测试与dense/异质K控制。每个正式比较同时保留最佳可用库与同体强简单基线。
正常主路径有6策略及首尾库锚，每case6独立块。没有强信号也完成预定24-case阴性确认，不继续搜索新形状。
有相同shape热重放，也有预先冻结的不同路由/shape序列；两者分别报告。GPU当前动态信息不能在计时前每轮从CPU免费提供。

### E4 融合×调度与完整MoE层（2.5h / 4h）
完成F0S0/F1S0/F0S1/F1S1及可用最佳库；F0是已有成熟融合，不是刻意劣化版本；F1只包含实际新增合法融合。
逐节点确认元数据/生产者膨胀、额外launch、等待和中间字节数。主比较 F1S1 对 F1S0，也对真实最佳层基线。
没有新增可融合点就跳过该因子、保留调度对照；如果两种实现相同就去重。
真实路由可用时从router输入计时；只能replay route时明确 `LAYER_POST_ROUTE_REPLAY`，不能说完整LLM收益。

### E5 不等长attention独立验证（2h / 3h）
使用成熟attention主体，先保持原segment划分、softmax/归并顺序。只改完整request/head或原segment任务的执行顺序；不自行重写FlashAttention算法。
plan/run成本按其真实生命周期处理：动态长度变化需要重新plan则计费；多层可合法共享plan时基线同样共享。candidate同样不能免费预知未来长度。
prefill仅做有限控制；decode为主。库或接口不支持修改则完成可运行原生与成本报告，标 `ATTENTION_ADAPTER_UNAVAILABLE`，不无限移植。

### E6 真实模型、漂移与生命周期（1.5h / 3h）
有本地模型且集成有效时，最多2个完整模型，每模型3类请求轨迹、3独立块、3策略加首尾锚。无模型不下载、不用随机权重替代“真实模型”，保留层级结论。
自回归时不允许从测试未来token/路由生成schedule。teacher-forced校验与真实decode性能分开标注。
报TTFT、TPOT/ITL和吞吐时写清终点；没有服务队列时不是在线SLO/排队p99。

### E7 机制、同融合强基线、数据与报告（2h / 2.5h）
最多8个代表性硬件profile/平台；缺计数保留UNKNOWN，不阻塞已合格因果时间。
根据调度消融、cache/轮次/尾部与完整成本决定哪些主张成立。没有physical placement不叫NUMA；只有融合收益交 `FUSION_ENGINEERING_GAIN_ONLY`，不是“拓扑算法成功”。
核对所有实际kernel launch、同步、plan生命周期、路由输入和输出。完成合并用summary，最终一次性返回报告。

## 6. 决策分支：不中途不断请求科研批准

A. 主体合格、候选有增量：自动完整E3–E7。
B. 孤立算子无增量但fusion/层可能不同：执行固定的缩小算子确认与完整层确认；不直接停在pilot。
C. 同体有增量、落后生产库：记 `SAME_CORE_GAIN_ONLY`，有限层确认后报告主体差距。
D. 只有fusion有收益：仍交付完整收益、成本和现有技术对照，不硬拼NUMA故事。
E. 某平台/attention无支持：完成可支持实验和明确缺项，不把NA填成0、不等待另一机。
F. 缺所有成熟主体或真实数学执行：完成CPU准备和一次资源清单，不能返回“实验全部完成/无收益”。
G. 发现明显与已知方法完全相同：保留复现价值和最小比较，不悄悄改题或跑满预算。

每个平台各自按冻结数据判断，不从另一平台test赢家选择本平台规则。必要的kernel参数可以按本机开发集调优，方法逻辑一致。

## 7. 预算、安全与不过度防御

T10总16 GPU-worker小时；5070Ti总24小时；每阶段分配见campaign.json，合计40小时上限。新付费授权0；已有租用机器的真实占用成本按单价记录，未知填null。CPU开发/分析另计，不承诺整项研发40小时完成。建议按数周的研究工作组织，而非把worker预算当开发工期。

一个GPU worker；复用进程锁，记录请求/获锁/启动/结束时间；等待锁不假装GPU并发。CPU编译≤min(4,物理核数/2)。应用留出max(2GiB,15%实际显存)；所有weights/中间/plan/workspace/Graph池均计入。

不为达到2ms审计目标人为拆碎原生算子；按普通kernel先小样例、渐进实际规模。有限循环和依赖按库语义执行，不关闭watchdog/改TDR，不人为制造超时负载。新device-lost/Xid/OS恢复立即停GPU并一次报告；CPU整理继续。

正常正确性与审计工程以约10–15%的研发精力为目标，而非新建框架；不能用这个比例豁免确实的越界/任务重复。只做3级检查：CPU映射小域、有限GPU完整数值、正式结果抽检与代表性复验。

不追旧图像差异，不要求所有跨库FP输出bitwise；使用docs/07预注册的数值与结构合同。普通缺工具/未知counter不是停整个项目的理由。

## 8. 最终交付

`OPERATOR_FUSED_SCHEDULING_REPORT_<platform>.md`，并附：
- `CONTRIBUTION_CARD.md`：一句待证命题、最近方法、真正新增能力、强基线差异；
- `KERNEL_DAG_BEFORE_AFTER.md`、`LAUNCH_AND_TRANSFER_LEDGER.csv`；
- `BACKEND_CARD.md`、`IMPLEMENTATION_DELTA.md`：实际改了哪个函数、是否留有额外planner；
- 算子、producer-consumer、完整层和模型四层表；
- 六策略与fusion×schedule消融，完整CPU/GPU/初始化/显存成本；
- raw/derived索引、失败、被跳过项、leaveout和实际预算；
- `summary_<platform>.json` 和简短导师稿。

不得把“实验通过了很多检查”作为论文主贡献。结论可以是正、混合、工程或阴性；零发现/无收益不追加无限新算法。当前授权的终点是完整数据报告，不是中间一个 Gate。
