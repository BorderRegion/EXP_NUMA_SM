# 位置×数据测量与实际控制：实现要求

这些是新实验方法的约束，不是已经确认的5080硬件结构。API语义来源见S2–S6；原论文见S1。

## A. 不再用一条SM0链判断NUMA

测量单位：`allocation_generation × cache_recipe × concurrency × sample_round × observed_sm_or_resource_group × region_id`。

对每个被测地址区域，必须从多个实际执行位置访问；对每个位置，必须访问多个相同区域。记录稀疏覆盖矩阵与每格有效样本数。只记录SM0、仅统计每SM总时间、block编号当SM、或各SM各测不同地址，都不满足本合同。

默认5个分配生命周期，前3个用于设计/校准、后2个作确认；3个工作集(0.25/1/4×实际L2)，ordinary与.cg两配方，稀疏/吞吐两并发条件，共最多60个stratum。每个stratum最多64区域、6个随机化轮次。32区域用于拟合，32区域作新地址条件确认；同一地址的前后轮次用于地图预测验证，两种验证不能互相代替。

先对本进程池内的4KiB/64KiB/2MiB**虚拟窗口**做一个有限粒度侦察；不称这些窗口为物理页，也不把区域平均没有双峰解释为所有细粒度无NUMA。最终采样粒度、间距和池布局在确认前冻结。整个池≤512MiB。

新分配确认分两种：
- `RECALIBRATED_ALLOCATION`：算法固定，对新分配执行必要的初始化标定，然后在后续轮次验证；标定成本计入。
- `STALE_MAP_TRANSFER`：只用于合法的新分配上的映射预测诊断，绝不解引用旧已释放指针；不能用新结果调旧地图再叫迁移成功。

至少报告：被实际覆盖的SM数/可见SM数、每地址覆盖位置数、每位置覆盖地址数、所有缺格。建议主矩阵目标覆盖≥80%可见SM且每区域跨至少两个候选组；这不是硬件不存在的判据。达不到时结论为样本不足。最多一次增加grid波次数或减少每CTA工作，仍在E1预算内。

## B. 可执行的自然采样方式

每CTA执行相同量的合法依赖访存，读出当前smid并记录地址区域与耗时。region顺序采用预生成循环置换/随机顺序，使不同SM不会永远对应同一缓存历史或轮次。

可用多于SM数的有限grid自然收集位置覆盖；也可在已支持的Green资源分区内采样。**不能通过过滤非目标SM后无限重发，或让不需要的SM忙等，假装获得无干扰单SM实验。**记录发起的全部尝试与成功覆盖；不只保留最快位置。

依赖链要让读出值决定下一地址，链内容runtime生成，结果参与checksum；确认生成代码保留load，合法使用PTX cache操作时先本地编译核对。不可用时标缺项，不替换成不同语义却保持同名。

线程内两次clock之差可作该线程elapsed-cycles样本；不能相减不同SM的时钟，也不能从局部ticks直接推整帧可节省ms。计入timer/loop控制对照。正式aggregate吞吐用CUDA event和逻辑字节计数。

## C. 缓存与并发：分别控制，避免热图是时间顺序

1. 普通load：代表普通生成代码，实际指令以本地产物为准。
2. `.cg`：意图绕过L1、保留L2路径；不意味着必然访问显存，更不意味着真实renderer具有同样访问。
3. `WARMED`：按固定配方触及指定数据，再测；原始consumer位置和producer/primer来源可用时记录。
4. `EVICTION_CONDITIONED`：只遍历自有较大scratch，作为降低热缓存影响的条件；**不称清空了全局L2或DRAM冷访问已证明**。无干预对照也保留。
5. 稀疏与吞吐负载分开。前者仍有调度噪声，不冒称绝对无人争用；后者混有排队/竞争，不能叫纯load latency。

每轮交错reference区域、随机化区域次序；不同策略使用同一priming配方，不总是先基线后候选。没有硬件counter时，cache层级归因保持有限。

如有两个可控资源组，再做有限的primer组×reader组交叉诊断：同一分配、同一地址、同一量、reader-only对照。它用于判断“先前读取复制了数据”是否造成热偏好；无控制则不强行做。

## D. 信号分析

建模：`L(s,r,e)=mu + sm_effect(s) + region_effect(r) + epoch/order/cache_covariates + interaction(s,r)`。

先去除位置主效应、地址主效应与条件主效应。对完整平衡子矩阵可用two-way centering；缺格禁止补成0或均值后声称观察到。

两组只是候选，不预设。比较K=1/2/4（样本与控制足够时），冻结算法并在后续轮次验证；新区域先只能验证组间差异，若为其选择home需要新区域自己的初始化读数，不能免费知道。

报告heldout同地址上的rank一致性、组偏好稳定性、正确匹配对平衡置换的预计差、独立分配重标定时间。bootstrap以allocation/process/round为簇，不能拿每条load当独立硬件实验。置换保持每组任务数和负载分布；group标签置换与随机任务分组不是同一个消融。

进入E2需要有**独立确认的实际交互**，而不只是显著sm主效应。参考阈值是目标访问模式下约3%可重复交互并超过计量底噪；这只是预算决策，不是物理NUMA定义。较小而精确的差异保留，只能降低后续投入预期。物理域未经文档/交叉证据确认就称`EMPIRICAL_AFFINITY_CLASS`。

## E. 控制后端1：公开分区优先

按本机头文件/库实际能力使用：
- 当前已存在的Green Context SM资源分组：获得的具体组是opaque资源；查询/观测实际SM集合，不把group0叫NUMA0。
- locality domain显式接口：仅当本机确实声明、库符号可用、返回支持时使用。在线新文档不代表本机13.2支持；禁止硬编码缺失enum整数或动态调用未知ABI。

按同一split产生互不重叠资源组，记录剩余SM、实际份额和排队资源；公平对照要使用相同总资源。分区granularity引起余数不能悄悄丢掉后声称全卡效率。group count最多4，第一版优先2组，但由信号和API决定。

每帧可有固定数量的分区launch与event衔接；这些成本全部在稳态计入。没有任何跨组kernel忙等。API不保证任意并发前进，先合法producer完成，再launch互不依赖consumer，最后host或GPU event汇合。

同一allocation可测“组A/组B访问同一地址”的亲和关系，即使没有内存域分配API；只有效果确认才在自有池中选择数据槽。首次写入者不是数据home保证。

## F. 控制后端2：有界cooperative roster（条件式）

只有本机支持标准cooperative launch、实际kernel资源满足grid限制、局部small-case/sanitizer通过时尝试。**不能把普通<<<grid,block>>>加软件barrier伪装成cooperative。**

一launch内的逻辑设计：
1. 每CTA拥有唯一逻辑worker_id；一个线程记录其当前smid/empirical group到独立roster槽。
2. 所有CTA参加一次标准grid.sync；这是可测的每launch固定成本，不是初始化免费步骤。
3. 根据完整roster计算各组实际worker列表、count和rank。不能假设84CTA恰好分散到84SM。
4. 初始化计划为每组建立不重叠任务list。若某组本次没有worker，按冻结的确定规则将整组list分配给实际存在的组；不能等待该SM、不能丢任务。每组内按rank/count做静态stride，不需要逐任务atomic。
5. 每个CTA处理自己被分配的有限任务。线程内所有tile同步保持完整；最后退出，不跨帧永久驻留。

必须有CPU枚举证明：任意合法roster（缺组/重复SM/不同数量worker）仍每个task恰好一次；GPU诊断counter验证。执行中smid变动只影响亲和性，不修改已确定的逻辑所有权，从而不引入重复/漏执行。

实际grid限制来自本kernel occupancy和cooperative API。不能无理由分配巨大shared memory只为了强制“一SM一block”；如需改变资源配方，所有matched对照一致并计入原生差距。

roster使方案满足Z0/Z1，但不满足严格的零per-launch开销。若它的成本抹掉亲和收益，正确结论是本后端不划算，不增加长期常驻、steal queue或未公开TPC masking救结果。

## G. 三类映射标记

- `DOCUMENTED_PHYSICAL_DOMAIN`：有受支持接口及实际查询依据。
- `CONTROLLED_EMPIRICAL_GROUP`：可控组且测得组×地址效应，物理含义未知。
- `ORDER_ONLY`：只能排列逻辑任务，无物理匹配控制。可作小型negative control，不进入NUMA主结果。

两类后端均不成立时，输出CONTROL_UNAVAILABLE并自动CPU收尾；不替换成另一篇缓存调度题。

## H. 额外有效性检查

- 为区分写入来源和读取来源，不把“由SM组A初始化的数组”预设为A本地；初始touch不是显存home保证。
- 每allocation的已观测区域表只适用于实际覆盖字节与粒度。把一页中的少数点扩展为整页/整数组，需要分层额外采样；不可验证处使用混合访问成本或UNKNOWN，不免费外推home。
- 同一资源组内SM异质性可隐藏相反偏好：同时保存group汇总与已观测SM明细，不能只报告平均后宣布无信号。
- 为了测低并发可以减少grid规模，但不得把覆盖不足当作“某些SM不可用”。为提高coverage可增加有限轮次，不能长时间占住其他SM来强迫位置。
- 地图只在自己拥有的存储与固定资源生命周期内使用，不获取他进程物理页，不绕过驱动接口。该研究是合法微基准与调度，不修改系统安全机制。
