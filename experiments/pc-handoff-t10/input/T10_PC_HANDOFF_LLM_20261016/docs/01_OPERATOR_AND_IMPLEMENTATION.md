# 真实算子接入、固定映射与无额外小调度 kernel

## A. parallel split-K 是首个可交付路径
本地 CUTLASS 入口优先：
- `include/cutlass/gemm/device/gemm_splitk_parallel.h`
- `include/cutlass/gemm/kernel/default_gemm_splitk_parallel.h`
- `include/cutlass/reduction/kernel/reduce_split_k.h`
- 相应Sm75测试/实例化文件。使用本地版本，不照抄网上未安装模板。

`GemmSplitKParallel` 默认模板可能是 SIMT/Sm70；必须显式使用本机合格的 `OpClassTensorOp`、Sm75及相应HMMA形状。验证SASS有HMMA只证明使用Tensor Core，还要与成熟库做速度对照。
普通FP16 A/B、FP32累积；默认FP32 partial与最终FP32输出。模型需要FP16时仅在共同最终epilogue转换，不能逐split先降FP16再相加而漏报语义变化。

整体为
`A,B -> P: partial[S,M,N] -> R: 按固定s顺序归并 -> D`。
partial每次覆盖全部会读取元素；没有scratch memset需要时不新加clear kernel。
`alpha`、`beta*C`、bias、activation只执行一次，在全部partial归并后。测试默认alpha1/beta0，另有限beta非零资格。

不要从高层 `run()` 复制出两个全量P；先确认原库已经发P和R各一次。需要位置控制时，改现成device launch adapter并复用实际kernel/Params；每个逻辑P任务只执行一次。

## B. 两个清楚、有限的实现层级
### B1 数学同体、无物理控制
正常全设备P/R，改变P输出和R输入的短算术布局；同样S、同样K边界。
这是layout-only对照，不能因使用同一逻辑owner编号就称绑SM。

### B2 真实可控的PC配对
重用现成本地Fine/Green资源构建，E2后确定两个等大、不重叠且合计全T10的资源集合。若硬件不同，按实际剩余SM记账；不丢资源。
给输出tile t一个简单owner，例如`g=t&1`（轮转）或`g=(t>=cut)`（连续半区）；只从这两种规则开发选一个。
**tile t的全部split s在P组g执行。**归并者在`C_group = pi(g)`执行；pi为identity或swap的冻结标量选择。
这一层保证跨CTA partial是同一输出的真实依赖，不把互不相关tile当作通信。
P组内任务 `(t,s)` 使用现成数学kernel及短tile偏移/stride，R组内读取对应完整输出tile。
原库reducer可能按连续元素块而非GEMM tile组织；必须修改其输入/输出iterator或范围映射，让一个R工作块只消费归属于本组的元素，保持其向量化/归约主体。不能仅改grid数量却遗漏部分输出，也不能每tile单独launch。若这个必要adapter尚未完成，要标实现缺口，而不是用数学上错误的分片做性能。
不根据blockIdx推断实际SM；诊断版每个P/R的logical tile/s记录实际SM，由资源约束和前后资格支持正式执行。
同组生产与消费不是同一个SM保证，更不是访问另一SM shared memory。

### DAG与全局依赖
默认对照保持：`fork -> P0,P1 -> 全部P完成 -> R0,R1 -> join`。所有策略同一global barrier形态，便于隔离位置。
实现为已在本机资格通过的异步stream/event或Graph；不在P/R之间CPU同步。父stream的起止事件在同一合法上下文；禁止减不同上下文的事件时间。
可选独立链版本：`P0->R_pi(0)` 与 `P1->R_pi(1)` 只依赖所需partial，允许早开始R；该变化是依赖收缩/流水因素，不是纯位置。最多做docs/03中的四格，不用于覆盖基准版本。
每次重放都重新计算P。绝不复用上次partial而只测R。

有两个资源组时最多4个实质kernel，而原生split-K通常2个。Graph中可能还有events/child节点，分类记录不只数总nodes。
不能称4节点为0额外launch；也不能每tile启动一次。如果控资源的4节点仅用于因果而慢于原生，准确报告实现路径的限制。

## C. 唯一布局家族：输出tile连续的partial slab
基线 PLANAR：按原库`[split][M][N]`及真实ld/partition_stride。
候选 TILE_SLAB：`[owner的连续tile范围][tile][split][element-in-tile]`，同一输出tile的全部partial相邻。

重要：生产者仍按原K片段顺序计算，每个元素的s归并次序固定为0..S-1；改变地址，不改变运算树。
producer epilogue直接写slab；reducer直接读。无transpose/pack中间kernel、无scatter调度表。
边界tile有padding时记录实际workspace字节和初始化；无效元素不得被无定义读取。纯位置消融使用相同layout/padding。
先完成无需owner类的普通TILE_SLAB基线，再加入资源匹配。若布局只有普通cache收益，不能称NUMA。
编译参数只有BM/BN/BK、S、group_count、owner方式与对齐stride等小量常量。设备指针在初始化绑定，不能把上个进程地址写进可复用cubin。
不把整个tile列表展开成巨型switch/code；每分配重新选择物理页不属于本轮。

## D. 选组/选方向：没有0x33，也没有任意任务表
E2用4个按公开资源对象确定、大小接近的组得到真实PC矩阵；不按SM编号远近解释。
开发期只枚举4组分为两组的3种等份组合（可加两种direction）。成本综合采用共同任务完整链与组配额，不以最快单task为oracle。
最多每算子族冻结一组资源划分和一个pi、一个owner方式。选择后在8个新进程重建相同SM集合；集合变更需新epoch而非静默换组。
同组G是强简单基线；若学习M选择的就是G，同实现合并为alias，不能声称新信息贡献。
某size可选pi在独立输入中翻转则按条件效应报告；禁止看到测试反向更快后重新命名。

## E. Stream-K不是另起项目
若本地有已经正确的SM75 Stream-K：保存既有work decomposition、flags、release/acquire、workspace生命周期和进度保证；作为强基线。
只允许复用原内部store/fixup的地址接口，不自行重写last-block/spin rendezvous，不用不保证并发的资源组让互等CTA陷入死锁。
本轮主路径不依赖Stream-K可改性；不要为移植第三个数学主体消耗全部工作。

## F. split-KV attention
读取本地成熟decode代码中的tmp output与log-sum-exp/normalization state、split和merge入口。正确对象是实际partial O和统计量，不是复制一个大KV数组作为替代。
对每request/head，拆成S段计算，局部输出/统计通过本来需要的workspace交付：
`o = sum(exp(lse_s - m) * o_s) / sum(exp(lse_s - m))`，`m=max_s(lse_s)`。
保持现成segment划分、mask、head映射、scale、partial dtype与merge顺序。空段lse=-inf、贡献0；不把全部空段变成NaN。
workspace布局和输出head owner遵循同一slab及PC规则；原始KV页表不是新调度LUT。
不自行在gate里做GPU结果D2H来选S；静态shape规则在init，动态长度由现有GPU描述符提供；新增必要plan成本全部计入。
仅有库封装、无法修改核心时只能称native参考，不冒充实现FULL。

## G. 能融合与不能融合
能：workspace地址生成在已有P epilogue；R读地址在prologue；最终bias/activation在R epilogue；必要常量一次初始化。
不能：在partial未全到时使用最终非线性；任意CTA等待其他未驻留CTA；省略真实split统计归并。
对照必须相同fusion。没有新增可融合点就如实说已有后端已经融合，而非拆坏F0。
