# 编译与提前布局：无运行时任务查询表

## 1. 本轮的算法对象
离线求得：实际执行域集合G、固定分配中的地址类别、无损布局函数phi、任务到域的可表示规则rho、剩余共享资源规则。初始化输出少量常量/模板参数与分配基址。

稳态：原生task/逻辑地址 -> rho/phi的算术或已有producer产生的连续域范围 -> 原数学kernel。
禁止稳态 `domain = home_table[page]`、`task = schedule[worker][i]`、SM组大数组查询，或每次动态排序再号称静态。
普通模型指针、CSR索引、GEMM descriptor仍然允许，但新增映射不能藏进它们后不记成本。

## 2. 可接受的表示，按优先级
A. **直接本地化连续分配**：官方接口支持且已验证时，选择域特化entrypoint与连续区间，访存是base+offset。准备期完成重排/拷贝。
B. **固定分配内验证过的算术着色**：在虚拟granule序号上拟合有限XOR/affine关系，或≤8个分段区间；冻结后独立验证。只声称该allocation上的经验模型，不声称破解了PA。
C. **低成本已有kernel内router**：每CTA/已有worker至多一次位置分类；使用编译立即数/短分支，处理原有连续工作范围。只有已有persistent框架能合法接入时使用。router额外的比较/原子/计数器都测量，不称零。

默认最多4域、8段/bit项、2个表示家族。不是让几万个任务变成几万个switch分支；二进制膨胀和寄存器是成本。

若实际home近似随机、无法在这些表示内保留独立映射能力，结论是**当前无查表要求与该映射不相容**。不偷偷上传LUT，不要求用户放松后再绕回旧方案。

## 3. 条件式无查表公式（只有符合前提才能用）
如果固定allocation的2^n个等大granule被独立验证满足
`home(s) = parity(s & MASK) XOR BIAS`，且MASK非零，选其中一个有效bit p。
对某域d的逻辑granule j，先在第p位插0得u，再令：
`slot = u | ((parity(u & MASK) XOR BIAS XOR d) << p)`。

该式可以精确保证：对两个d，各覆盖一半槽位，二者无重叠，合起来为全体槽位。这只是位向量代数保证。
**实际哪些slot靠近哪个执行域，仍然完全取决于前述独立测量，公式不会创造NUMA。**

本包CPU参考可验证双射和生成公式。它不含任何T10/5070Ti hash；禁止把数学自测当成真实硬件mapping验证。每个被访问granule内部也可能混合home，需细采样；查不到部分标unknown，不自动推广整个页。

数据重排后的CPU参考先逆映射再校验。任意公式都可以保持数学正确但性能无效，二者分别验收。只存被选中的一个layout，不免费复制全部数据到每域。

## 4. 计算放置不能省略
### C-A：公开资源限制＋每域实质计算entrypoint
创建时固定资源组，记录其实际SM集合。每域kernel是完整的大计算工作，不是额外的“调度kernel”。通常2–4个数学分支；它们与单全设备kernel的数量差全部计费。

按本机API支持，用已有producer的event fork、各分支计算、consumer前event join，不在每个分支之后先做CPU synchronize。支持合法Graph则在初始化捕获/构建，同样给基线；旧13.2接口与在线新locality API不可混用，先查询编译。

域ID写入template/entrypoint，不在每任务查表。个别分组过小不能悄悄丢弃；份额、剩余工作、实际执行都计入。

### C-B：已有单kernel persistent框架内的router
只有现成主体适合时才接入，不从零写慢的Q执行器。读位置一次，常量分类；以原有scheduler为基础分配连续域工作。
如果静态worker覆盖依赖实际roster，不能假定全SM到齐。允许在同一次合法cooperative launch做有限初始化，但不能把roster扫描成本隐藏；不允许普通grid自旋barrier。
若用少数域范围计数器作批量领取，原子领取结果是唯一逻辑所有权，某home暂时无worker时其他worker必须能有界处理其剩余工作，无忙等。这样可能存在远端fallback，必须记录，不能宣称纯静态零原子。
这条路径不能引入每task数组或把新计数器reset变成每帧独立小kernel；复用已有安全初始化/producer，或选择C-A。正确性不依赖SM标识终身不变。

最多实现两个候选控制入口；只选择一个进入主矩阵，另一个做少量开销对照。

## 5. 动态任务和生产者
固定权重/矩阵可在加载时布局。动态输出不等于必须动态求全局亲和计划：编译规则可固定，原producer按该规则直接写布局。

只有分区依据已在当前线程/CTA合法可得时才能顺带生成目标地址/小描述符。全局counts/scan未完成不能在GEMM epilogue等它；沿用本来必要的全局边界，修改已有pack/scan的输出格式，不新增独立planner。

如果任意动态task需要新任意排列才能本地化、又没有合法便宜的producer，记录这个负载不满足本轮表示，不假装静态。如果只支持固定场景/矩阵，准确报告有效期。

## 6. 不破坏成熟访存机制
映射要保持连续load、对齐、向量化和合法MMA输入。逻辑连续一段在物理上跨色缝时，不能继续执行跨缝vector load/TMA当作连续数据。
优先令映射granule与MMA复制tile兼容，在iterator/prologue一次计算piece基址，随后保留原内层指令。不能把每个标量load都套popcount然后声称没有成本。
SM75、SM120的库代码分别编译核查，不硬套新架构TMA/MMA。

## 7. 计划生命周期
有效键至少：GPU UUID、驱动/实际API资源组、binary、allocation generation、布局参数、模型/矩阵身份、尺寸容量。runtime host在资源事件检查，不在每个load查。
重新分配/容量增大时执行一次必要重标定或native fallback，成本入账。不得读释放指针；只把旧地图作为对新合法内存的预测诊断。

## 8. 真正落地要交付的证据
原始测量 -> 拟合参数 -> 编译源/命令 -> cubin/SASS -> 位置与数据实际匹配 -> 输出 -> 完整时间。
用反汇编和source核查无调度LUT的load链；所有额外访存、分支、原子、launch单列。仅文件名含constexpr不算通过。
