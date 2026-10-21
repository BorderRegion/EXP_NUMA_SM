# 静态计划、数据生命周期与“写死kernel”的实现边界

## 1. 固化的三层内容

| 生命周期 | 可固化内容 | 不能免费固定的内容 |
|---|---|---|
| 设备/工具配方 | 可用控制后端、资源组能力、SM组的经验关系、kernel模板 | 每个进程实际SM部署与任何分配的物理home |
| allocation/scene generation | 长期buffer布局、合法task列表、拓扑/数据匹配、小型只读表 | 分配重建后的home、测试未来帧的任务列表 |
| 每帧 | 只更新相机与原算法正常输入；执行固定映射 | 不重新分析ranges到CPU，不逐帧规划/重JIT/上传完整schedule |

数据在每帧变化不等于物理地址必须变化。应复用有容量上界的buffer；容量增长产生新的generation并使地址地图失效。所有策略有同样容量策略，不允许候选过度预分配而不记显存。

## 2. 两个特化层级都要测

### T：初始化table
一次性保存 `group_offsets/task_ids`、任务→组、布局slot映射与计划fingerprint。每帧只读。device base pointer作为参数，不能缓存旧进程绝对地址。

### K：compile-time常量／模板
同一个已冻结计划，能形成小表达式的offset、stride、组数和配方作为constexpr/template；不规则的大表仍是只读数据，而不是数十万条展开代码。T与K输入、逻辑task分配和输出相同。

最多8个预定模板组合，各种基线得到相同编译/调优预算。保存编译wall time、cubin size、指令/资源摘要；K若被编译器生成得与T相同是有效结果，不阻止其优化。禁止volatile或禁优化来制造差异。

若K资格失败而T有效，继续T并报告K未通过；不能临时放宽浮点容差。没有新native ISA数据，不能从PTX简化推导硬件一定省开销。

## 3. 数据布局家族：最多一种可证明双射的无损映射

第一优先不改变物理布局，只对当前实际allocation建立亲和表和task分配。若缺少匹配可利用数据，再条件式选择一个`logical_id -> (shard, slot)`无损布局家族：
- 只操作本进程内真实存在的数据槽，每项逻辑数据恰好一份；禁止复制整场景到每个域并称零成本。
- 有公开本地分配API就用它；没有时只可用自己分配的池中实测的slot/区域，不声称得到物理地址。
- preserve alignment和连续访问；插孔/重排可能损失coalescing或TLB，实际容量与访问指令计入。
- 不把4KiB虚拟窗口普遍当成单home物理页；观察到混合的chunk不强行贴标签。

布局与assignment应做2×2消融：原布局/候选布局 × 盲分配/正确亲和匹配；matched置换保持逻辑字节、资源份额、每组任务数和尽可能相近的work分布。不能让置换顺便生成更大的任务尾部后，把全部差解释为NUMA。

## 4. 3DGS接入：三个证据层级

### L0 固定地址索引机制
从synthetic uint任务或真实快照索引读取固定数据，CPU给精确答案。可知道全部输入，用于验证硬件机会与控制；不称完整渲染。

### L1 固定render快照
正常上游得到 `ranges/point_list/means2D/conic_opacity/colors`等，再冻结地址与内容，比较完全相同tile evaluator。每个快照可有自己的初始化plan，准备、复制和编译都单列。不能跳过上游后仍称每帧pipeline。

### L2 正常动态相机渲染（主要paper证据）
每帧仍运行原preprocess、scan/binning/sort，更新投影/颜色/列表；固定task规则和buffer布局不能读取测试未来列表。保持point_list中的原逻辑Gaussian ID与所有排序tie。最多只修改输出物理slot与consumer读入映射，不重排原高斯处理次序。

每帧上游如果需要新slot计算，这是候选稳态成本。新scan/排队/散射pass不是免费，违反Z2时如实降级；本轮不为此开发第二个新算法。

## 5. 静态任务特化方法：一个小而完整的候选

在最多16个开发相机上收集tile→资源引用和工作量信息（训练成本记录）。冻结后以tile逻辑位置为稳定task key。工作量可用candidate list length分布；它只是估计，不能称实际贡献数。若观察了实际运行成本作offline特征，所有同级基线获得同信息，计入init成本。

使用实测交互矩阵 `c[g,r]`，而不是人工给“local 1、remote 2”。记录每资源权重来源，地址/类型字节不冒充DRAM流量。

对assignment `g(t)` 最小化预注册的保守完成时间代理：
`max_g sum_{t:g(t)=g} (compute_est[t,g] + sum_r access_weight[t,r]*c[g,r])`
再用固定开发相机集合的均值＋尾部惩罚聚合；最多8种系数组合，与基线等预算。实现使用有界贪心＋一轮pair swap即可，不引入LLM/RL/全局求解框架。

候选的新颖性待证：这个公式本身是已知的静态分配思想。必须报告它是否产生了区别于简单亲和+常规均衡的实际assignment；若退化为同一规则，按工程结果。

### 防止再次出现“公式里有，运行中没有”
每个score项记录range、非零次数、改变候选排序次数。硬constraint若使某惩罚项永远为0，明确删除该主张；不能重复旧Q的恒零tail项。训练CPU时间没有上限免费豁免，所有必要工作进入C_init。

## 6. 主策略集合与公平性

| ID | 策略 |
|---|---|
| N_NATIVE | 当前可用优化原生renderer/原生kernel，无新控制后端 |
| I_BLIND_MATCHED | 与候选完全相同控制/数据表示/launch，静态identity或round-robin；无亲和使用 |
| S_SPATIAL_STATIC | 相同机制的Morton/空间邻近计划，初始化一次 |
| L_LOAD_STATIC | 相同开发信息的静态负载分配；不使用亲和 |
| A_SIMPLE_AFFINITY | 按实测home和资源份额的简单静态NUMA/亲和分配，再用常规均衡；对应原论文式强机制基线，不声称完整复现 |
| T_JOINT_TABLE | 唯一联合候选，初始化表 |
| K_JOINT_COMPILED | 与T同一个计划的常量特化 |
| P_PERMUTED_AFFINITY | T的同binary匹配置换对照，不重算任务搜索；平衡总工作和资源 |

若有新的内存布局，I/A/P也得到同布局开销以做matched归因；Native独立保留原布局体现部署比较。仅M比慢I快不算净收益。

相同数据、线程block大小、算术、编译优化和precision；不得给N保守编译，给K fast-math。代码生成会有差异时保存双方cubin/资源并独立资格，不用“same binary”妨碍真正特化。

校准阶段选B*=I/S/L/A中最强合法静态方案（Native仍单列）。测试前锁定B*、T/K及次序，不能对每test场景换赢家作为部署策略。可事后算理想包络，但标`TEST_ORACLE_NOT_DEPLOYABLE`。

## 7. 初始化与生命周期计费

分开记：
- `C_research`：一次研究时的完整测量和算法开发；不冒充每次启动开销。
- `C_device`：真实用户第一次用当前硬件/工具配方必须做的标定。
- `C_allocation`：新allocation上的home检测与布局准备。
- `C_scene`：场景校准、静态task计划与数据移动。
- `C_compile`：生成/加载特化kernel的真实成本，包括无缓存/合法缓存两种情况。
- `C_launch`：每launch roster、额外event/partition launch；进入T_frame，不摊成一次性。

若实际部署还需要完整4小时E1信息，就必须把必要部分算入C_device；不能仅因为研究已做过就填0。若设计短初始化探针，必须用冻结算法与独立分配验证它能替代完整地图。第一轮只允许一个预定简化探针，不加第二研究项目。

比较：`C_extra + sum(T_specialized_f)` 对 `sum(T_native_f)`；同一个用户生命周期的共同场景加载可相消，候选额外数据放置不可消失。报告N=1/100/1000/10000的估计，测得N子序列另标实测。

若稳态`T_spec >= T_native`则没有靠延长N获得回本；若更快，严格回本最小整数N满足`N*(T_native-T_spec) > C_extra`。性能区间跨0时回本可能无有限上界，不能只给乐观均值。

## 8. 有效期与失效

plan绑定GPU UUID、driver/toolchain/cubin、控制资源配方、scene逻辑哈希、allocation generation、capacity与映射版本；逻辑指针相同不代表同一次allocation。

地址/场景/容量改变时，host在已存在的资源管理事件中标失效，使用已验证的Native回退，再执行计划允许的重建。无需每帧扫描完整资源、重复哈希或重新标定。相机改变不自动触发重新规划；它正是静态方案需要承受的测试条件。

必须记录：native回退帧数与成本、更新频率、错误共享/陈旧指针避免证据。禁止对测试视角偷看每帧最佳映射；不通过每次相机变化重建plan后继续宣称零在线规划。

## 9. 资源准备不与方法比较混淆

已存在Train/Bonsai/Truck与Toolkit的最新记录优先；只核对文件/版本，不能再运行整盘搜索或请求重复下载。若B/T需要在同一进程保留两种数据视图做资格，它们的额外harness内存单列并在所有时序对照保持一致；部署峰值还要在各自真实生命周期测量。不能借另一视图的缓存热度或未计费复制使候选占优。

每次重建/布局调整保持逻辑内容固定、原始Gaussian身份固定。部署只要求一份实际候选布局时，不把审计用reference副本误算成方法必需；反之方法真正需要的副本和跨域传输不能排除。
