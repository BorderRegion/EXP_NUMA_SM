# 给 T10 Codex：6–7小时同 q 因果验证与数学主体恢复

## 0. 任务性质与优先级

输入已经完成真正SM75 Tensor Core grouped实现。当前 `SAME_CORE_GAIN_ONLY / MATH_BACKBONE_GAP` 是合理边界；本轮不要把它改成NUMA失败，也不重新做纯库大矩阵。

论文问题不变：在高效推理算子内部，以不增加小调度kernel/CPU往返的方式改善工作组织。现在先补齐最接近的同q简单基线，判断正效应是普通遍历顺序、包长选择、编译资源还是新信息。

本轮只有一项必做实现：**独立的最小 q=1/N-panel-major visitor**。它不是被命名为新方法，而是简化对照与可部署候选。可做至多两种成熟tile实例和一个局部activation融合，不开发新自适应算法，不调高work_budget救q>1。

连续工作目标6.5小时、硬上限7小时。这个预算包括开发/构建/运行/分析和正常等待，不意味着必须采集满6.5小时。GPU-worker新增≤4小时且受旧16小时总账剩余额度约10.5305小时约束；读取实际账本后计算。最多一worker，现有锁复用。到期完成已有证据报告，不能为了凑矩阵延期或找用户批准普通分支。

## 1. 必須保留

- 原zip、raw、freeze和FULL=qcap1的事实不改；新目录 `implementation_same_q_v2/<run_id>`，追加registry。
- 当前已授权100W、风扇/过温/低转速/watchdog全部保留，不锁频、不修改保护。
- 当前CUTLASS v3.5.1 pin与成熟数学体优先复用。之前获批的下载不追溯否认；本轮无新网络/SSH/安装/远程Git/租卡。
- 缺工具记一次；已有本地profiling可用就用，不为硬件计数器停整个任务。
- 所有最终性能候选位于grouped kernel内部；不新增planner kernel/D2H/每expert CPU发射/算子内部全设备等待。
- 结果边界一次同步和数学必要的kernel边界允许，全部计时；Graph给所有方法相同使用机会。

## 2. 顺序任务与工作时间分配

|阶段|计划分钟|必须交付|
|---|---:|---|
|S0|20|冻结输入、旧结果修正口径、最小接口清单|
|S1|80|同q visitor和精简版本、必要数值资格|
|S2|70|高效主体有限诊断／适配、冻结数学配方和简单策略|
|S3|100|同q主比较与少量新输入确认|
|S4|65|完整post-route层、合法activation融合及输入ring分支|
|S5|25|独立分析、原始数据索引、论文判断与5070Ti交接|
|机动|30|只用于上述任务中有具体证据的修复/补充，不增加题目|

合计390分钟。420分钟是硬结束边界，最后30分钟只容纳收尾，不能用作新探索。检查/重复整理尽量≤35分钟，除非发现真实语义错误。

## 3. S0：不重搭工程，只把对照定准

核对现有 `.so`/CUTLASS版本、当前设备和100W状态；不重新扫整盘、不重新跑57项旧计划检查。记录两个独立事实：数据验证通过；方法归因为未识别。

从 `packet_visitor.h` 实际推出：qcap1与CACHEq1都是m=r%gm,n=r//gm；总tile/waves/K预算不改变映射。输出一张每个变体的“问题序列、tile序列、worker步长、是否读取总tile”的对照卡，≤1页。

把旧开发/测试全标为已知回归输入。新一轮的选择与计时协议在GPU新结果前冻结。旧主要数值不要重算覆盖，只可引用本包复算作为背景。

## 4. S1：建立真正的同 q 对照

### 4.1 需要的版本

- `CORE_ORIGINAL`：原生CUTLASS grouped visitor，原顺序。
- `CACHE_Q1_LEGACY`：现在的 `Full=false,q_cap=1`。
- `FULL_Q1_LEGACY`：现在的 `Full=true,q_cap=1`，保持旧waves2，用来复核残余信息成本。
- `Q1_MINIMAL`：相同N-panel-major tile映射，去掉无用total_tiles/K-budget/waves/packet state。
- `CACHE_FIXED_BEST`：已有q1/2/4在新开发集选出的最佳固定规则；与上面重合则alias去重，不重复计时。
- `LIB`：同一静态描述符范围内，校准选定的成熟库路径；保留PER_EXPERT_GRAPH、原生grouped的校准证据。

可另保存旧FULL配置作历史锚，但不可增加名称相同的重复phase。不能继续只拿q1对q4就叫新信息消融。

### 4.2 Q1_MINIMAL实现要点

复用原生problem发现与前缀机制，只改变合法tile ordinal到M/N的映射。没有内核外列表构建，没有运行时计数规约，没有总tile sideband，没有新增数组或工作队列。

`problem/within-tile accumulation/alpha/epilogue` 保持不变。同一数学配方下，每个logical tile的worker归属和访问次序必须与CACHEq1/FULLq1相同。必要时按现有类模板做最小派生/复制，但不要引入新框架。

如果q1-minimal编译后仍保留总量或packet查询，检查参数/类型是否真正常量消除了这部分，而不是仅在Python层改名字。记录compiler资源和小段SASS结构；不要用静态指令条数直接解释动态速度。

CPU映射小域与现成count_visits验证恰好一次；GPU选已有空expert、M/N尾块、65experts和改输入Graph资格点。只做有限完整数值比较和一次已存在sanitizer的小样例，不重跑整个资格矩阵。

### 4.3 不以融合实现错误来放行

q1-minimal不需要sideband，因此不要仍每步生成它再称fusion节约。如果新最小版在同数学体上不一致，允许两次具体定位修复；仍失败则保留CACHE_Q1_LEGACY，继续可支持的同q计时与主体分析，而不是所有任务中断或放宽容差。

## 5. S2：HMMA已成立，接下来查吞吐而不是再数HMMA

当前主配方64线程/CTA、3blocks/SM上限，即6warp/SM；另配方8warp/SM。高寄存器／有限驻留只是线索，不直接判根因。不要使用maxrregcount强迫spill、禁优化或降低精度。

### 5.1 必做诊断

对最多6个结构代表输入，将相同单problem分别交给：
1. cuBLAS/现成LIB；
2. 同tile的普通CUTLASS单GEMM入口；
3. grouped count=1/原生visitor；
4. grouped count=1/q1-minimal。

保持dtype、transpose、alignment、beta与数学范围。单GEMM入口可以复用已有本地CUTLASS示例，不按expert分次发射作为候选生产路径；这是限定归因诊断。

目的：普通同tile也慢，优先怀疑tile/math-instance/内存管线；普通同tile快、grouped明显慢，才有依据定位visitor/持续执行资源。单problem没有天然相同跨CTA次序，解释保持限定。

本地host-precompute grouped最容易接入时，可作为固定描述符附加对照；最多一次小实现，明确初始化/工作空间，不冒充GPU动态路由方案。若需要大改则跳过。

### 5.2 数学配方的有限适配

保留现有32×128和64×128，允许新增至多两种本地SM75合法成熟实例：优先32×64×32和64×64×32，warp32×32×32，instruction16×8×8，两级pipeline。若本地模板不支持，不伪造实例，不换到SIMT。

所有映射在选定数学配方上共用同一MMA/epilogue。数学配方变化的收益另列为engineering，不叫调度效果。对每个配方记录BM/BN/BK、worker规则、active blocks上限、线程/寄存器/shared、逻辑尾块浪费和实测时间；不要把理论occupancy称为achieved。

**BN从128变为64时，必须统一清除所有硬编码128：** host total_tiles、count_visits前缀、packet统计、sideband up/down计算、CPU模型、graph参数与summary均读取真实BN。不要只改template就让覆盖和sideband错位。若无法在预算内安全泛化，放弃新配方，保留原配方与真实缺口。

### 5.3 校准不再缺少整个K/分布域

本次是新开发轮，不能声称旧留出仍未见。用 `cases_v2.json` 中12个新开发机制输入，覆盖3种K/N、4种路由分布。3块短测即可，6块留给正式。不要从旧正例中选开发集。

两张报告都保留：
- 一个全局数学配方＋全局固定q的主结果；
- 如有必要，最多“低M/常规M”两个预定义shape-bin的初始化dispatch选择，仅用开发数据选，所有基线共享机会。

主归因仍在同一配方/worker上比较。不得使用测试timing逐case选赢家。冻结 `BODY_AND_BASELINE_FREEZE_V2.json` 后才读新的确认结果。

q预算规则保持原样。q>1没有适用点可以报告，不调大128强行制造；fixedq2/q4是正常机制基线，不当作新算法。

## 6. S3：最小而充分的主比较

优先执行12个预定旧回归输入和6个新确认机制输入，最多18case×6独立进程块×(最多6个独立策略+2个LIB锚)=864phase。

主要策略来自S1六项，alias要去重。LIB在平衡序列中有一份主测量，首尾锚只描述漂移，不能择优替换分母。6个唯一策略可覆盖6个位置；有5个时采用10行Williams中预定6行并如实记录未完全平衡，不声称所有carryover已消除。

每phase真实路径热身≥64次且≥150ms，算子测量目标累计50–150ms，重复数从LIB pilot一次确定，并对同case全部策略共用。允许32–256次，不为凑50ms拆碎kernel或串进额外同步；大case自然超上限时保留实际时长并减少后续计划次数，不按观察的速度选择谁多跑。

把外层Python/Graph提交空档与GPU事件跨度区分。CPU-ready与CUDA-event同时报告；正式phase只在批末等待，不能每tile/expert同步。条件允许时以一次Graph内重复多个完整调用减少CPU提交空档，基线/候选同享；其结果标均摊延迟，不伪装真实请求p99。

主要比较：Q1_MINIMAL/CACHE_Q1、FULL_Q1/CACHE_Q1、Q1_MINIMAL/CORE、Q1_MINIMAL/CACHE_FIXED_BEST、Q1_MINIMAL/LIB。FULL_Q1与CACHE_Q1的结果是实现开销/代码生成对照，不是不同自适应算法。q1-minimal失败时用legacy CACHEq1完成其余合法范围并明确NA。

新adaptive规则没有被授权；不要用7小时窗口重新发明一个q模型。如果有同体信号但仍落后库，照实报告，不选单个正例替换全域。

## 7. S4：在真实层上闭合，不只停在kernel表

固定4个已知回归层：moe_layer-007、009、017、024，覆盖小/大、旧正/负，选取已经公开，不称独立发现。每层6块、最多4个独立策略+2锚=144phase。新payload种子，路由明确保持或更换并记录；不同seed不能冒充独立模型。

必须包含LIB、同q简单版、q1-minimal、legacy FULL（必要时alias）。无sideband的主q1路径直接跳过总tile生成，而非在计时外免费准备它。

### 可选但优先的真实局部融合（在本阶段剩余时间内）

当前SiLU和multiply是两个必要pointwise阶段，可以将SiLU计算并入原multiply消费者，替代二者为一个pointwise kernel。它在完整up结果就绪后执行，不在某个GEMM CTA内跨CTA读取另一半gate/up；不增加新的kernel边界。

保持原FP16物化语义：先得到原语义的SiLU值并round到FP16，再与up相乘并round到FP16；不要直接在FP32里一口气算完后只round一次。禁fast-math/近似exp替换。先复用现有FP64+显式half边界参考，再做同体精确检查；原合同容差不事后放宽。若无法在20分钟局部实现内保持合同，就标未实现并测原层，不继续追exp低位。

融合不是新论文方法。必须同时给同q简单策略与q1-minimal同样的activation融合，使用2×2：S0/S1×原pointwise/融合pointwise。若schedule差别已被同q对照消除，就只报告工程融合，不制造四个同义策略。

### 输入变化最低确认

在两种较小层上，预先生成8或16个activation/route-replay输入槽，共用同一组权重；输入与准备都先说明生命周期。可以固定counts只换activation，标 `DYNAMIC_ACTIVATION_FIXED_DESCRIPTORS`；不同route/count若通过预先建好的Graph库回放，标 `PREPLANNED_POST_ROUTE_GRAPH_POOL`，不是在线动态router。

正常请求里的selection/copy入CPU-ready计时，所有方法机会相同；不清cache、不无意义复制权重、不超显存。若来不及，不扩成新的GPU prefix系统，说明完整动态模型仍未建立。

## 8. S5：必须回答的问题，而非一个笼统STOP

1. q1的FULL和同q简单版是否还有可复现差别？
2. q1-minimal去掉冗余状态/查询后是否真正更快？
3. 原native-order到N-panel-order是否具有稳定价值，在哪些shape成立？
4. 比库慢的主要证据指向数学实例、grouped visitor还是层外成本？哪些仍未知？
5. 改小tile或普通单GEMM对照改变了多少？有没有给candidate独享调优？
6. 在相同融合等级的层里是否仍有新增调度收益？
7. 冷/热、输入变化和固定描述符分别测了什么？
8. 有没有本轮没有新增小调度kernel、等待、D2H的源码和DAG证据？
9. 当前是普通遍历优化、主体工程调优、已有fusion，还是确有独立方法增量？
10. 给5070Ti能带走的方法/反例与不能外推的硬件配方是什么？

终态可同时标注：`Q1_ORDER_EFFECT_ONLY`、`Q1_IMPLEMENTATION_OVERHEAD_FOUND`、`BACKBONE_REPAIRED`、`BACKBONE_GAP_REMAINS`、`FUSION_ENGINEERING_GAIN_ONLY`、`NO_INCREMENT_OVER_MATCHED_BASELINE`、`METHOD_EVIDENCE_UNRESOLVED`。不要仅凭某个百分比输出paper-ready。

如果同q两方案打平，且精简后仍远慢于库，结束当前候选的扩展；不能自动换工作集、上ML、重做NUMA热图。若有真实新增能力，给出具体强基线差距和待独立验证部分，仍不宣称已经是新论文。

## 9. 计量、日志和权限（保持轻量）

复用现有worker/lock/JSON/Graph工具。新增字段限于变体语义ID、真实BM/BN/BK、实际q直方图、数学体hash、读取总量/sideband次数的源码标识、实际节点数、input-sequence ID。不重新hash全部vendor每phase，不写庞大新schema。

正式计时不插clock/smid/digest调度kernel；每phase后完整输出核对、每块少量位级样本足够。CPU模型、1次有限sanitizer、阶段末输出，是本轮必要资格。发生真正错误则隔离受影响版本，不污染其他已合格结果。

保存实际power-limit与每phase时间边界，100W不等于锁频。保留所有漂移块并报head/tail敏感性，不用温度回归修正速度或按胜负补跑。事先因健康/资源异常取消的尝试保留status，与真实benchmark区别。

每个run绑定当前构建文件和依赖，使用不可变build路径而非在计时中覆盖.so。旧62/30条账本保持前缀，追加本轮；时间预算到期安全结束并产报告。无counter不阻塞可信对照，但不能声明cache hit/DRAM/spill根因。

最终交付：主报告、同q等价/成本卡、主体分解、所有case正负结果与统计、同融合层结果、源码diff与关键SASS/资源、原始数据索引、预算、缺项及一页导师稿。不要再只给“FULL未实现”——本轮已有FULL，需准确说哪个补充未完成。
