# 02 容量曲线与kernel接入合同

## A. 这不是物理屏蔽实验

真实GPC0/3是10SM，1/2/5是12SM。原生10对12还混合GPC身份和其他未知因素。主要可控证据应来自**同一个12SM GPC里限制参与资源为10SM或12SM**。这只改变kernel可使用的资源，不关闭TPC、不重连芯片；不能证明制造屏蔽的因果作用。

本包`tools/plans.py subsets`根据当前CSV生成完整TPC的循环子集。同一12SM GPC，六块让所有TPC各被排除一次；每份输出保存SM/TPC/GPC和来源hash。当前CSV若不再是历史56SM形态，停止套用历史资源规则，报告拓扑generation变化，不猜新映射。

## B. 微负载怎么写才不测错

使用现成向量micro核，固定128线程、120和240CTA，资源2–12SM时总字节、循环、grid、输出不变。

|配方|真实消费|作用|
|---|---|---|
|HOT2_DEFAULT|同一次kernel读完整2MiB，循环16遍，默认16B load|热复用条件|
|HOT2_CG|同体，仅合法.cg向量配方|L1-bypass控制，不保证全L2命中|
|STREAM32_CG|完整32MiB单遍|大集合吞吐|
|STREAM128_CG|完整128MiB单遍|更大集合控制|
|REG_FMA|固定小输入、8条独立FP32累积链×128轮|计算/前端对照，不代表Tensor Core|

所有load参与输出，vector 16B对齐，尾部合法；不得把很多128KiB短核拼成“128MiB压力”。不要为n=2缩小grid。生成SASS核实load、未消除的算术和spill；主路径没有SM/clock/store诊断。输出校验放在suite外。

28资源条件×5配方×2grid×6块=1680主phase，另5×2×6=60个全56SM参考。默认全部报告，不只报告最有利n。若需缩减，先删STREAM32与REG_FMA的第二grid，保留同GPC10/12、HOT2/STREAM128和计算控制。

从C_g(n)=有效逻辑工作/T_g(n)计算效率。不能把HOT的16倍逻辑读取称为16倍DRAM流量。关键比值：C_g(12)/C_g(10)、[C_g(12)/12]/[C_g(10)/10]；后者接近5/6且前者接近1才与总容量提前饱和相容，仍需控制运行状态及前端因素。

## C. GQA已有代码的具体接入点

本轮核对过的旧 `gpc-contention-gqa-t10/src/gqa.cu` DIRECT入口：

```cpp
int head   = blockIdx.x / W;
int worker = blockIdx.x % W;
// 原页遍历不变
page = worker + iteration * W;
// partial索引仍包含全局head、原worker、原W
```

**允许的唯一数学外层修改：**

```cpp
// 每个长期资源组初始化时得到两个整数，或者同语义编译常量。
int task = task_begin + int(blockIdx.x);
// 实际launch grid=task_count；没有逐task路由表。
int head   = task / W;
int worker = task % W;
```

W、worker身份、page序列、partial布局、merge读取0…W−1的次序一律不变。前景全部B×Hkv×W个逻辑任务完整划分为最多五个连续区间，每区间一个实质producer kernel。最末仍由既有merge产生完整输出。总体五producer+一个merge必须完整计时，不能把Graph一次提交叫一个kernel。

两个标量是一个launch共享的范围参数，不是每任务数组查询；若编译常量化，不为每个请求重新编译。没有用SMID派单，没有新增持久化执行器、共享队列、自旋、48KiB驻留占位或人为减少原CTA数。

### 必须保留BLIND强对照

历史LONG/GQA8的最快默认可能是BLIND队列。它并不等于DIRECT。不能把全球双队列拆成每GPC队列而声称未改算法，更不能让各组重复领取相同页。

本轮受控容量比较用已有向量DIRECT数学体。N19仍使用历史真正较快的DIRECT/BLIND/融合路径；E56_DIRECT是新range入口的全设备DIRECT。由此分开：

- N19→E56_DIRECT：动态任务组织/融合/入口差额；
- E56_DIRECT→SM_PROP：五个资源组和有界额外launch成本；
- SM_PROP/EQUAL→CAP：容量信息的新增价值。

若新DIRECT范围入口明显慢于旧DIRECT，检查只允许一次有依据的wrapper修复；不得更换数学/worker数去抢救结果。已有DIRECT仍比BLIND慢就报告，而不是削弱N19。

### KV写入和归并

复用现有非融合producer+merge用于同体六策略；N19保留它真正的原融合等级。当前写入页仍由其唯一原worker执行；请求长度和新值在必要依赖之前已可见。所有组写同一partial的各自唯一worker槽；merge等全部producer结束才启动。不能在某组epilogue假定别组已完成，也不提前施加非线性。

对于原最后到达单核SHORT，保留为N19强参考。受控多producer首轮不用自己重写last-arriver协议；已有非融合路径就是成本诚实的参考，不宣称其负结果排除了所有未来融合实现。

## D. 连续区间如何产生，避免新查表

固定task顺序 `t=((b*Hkv+hk)*W+worker)`。建plan时有每序列有效长度或声明容量，可在CPU计算每个worker的预计有效页数：`max(0, ceil((ceil(L_b/16)-worker)/W))`。

本轮统一工作proxy为 `max(1,有效页数)`，最小1保留空worker写partial等固定工作。各策略都使用这个相同proxy；只是分到各GPC的总份额不同。容量分配不是为各task单独查询耗时。

按累计proxy在目标份额处取最近合法切点，五个边界完整覆盖任务，保持顺序，至少一个task/组（任务不足五组则该case不适合本控制，走N19并标记）。GPU只拿begin/count；CPU任务列表用于构造和审计，不上传GPU。

- SM_PROP：权重[10,12,12,10,12]，顺序为物理GPC[0,1,2,3,5]。
- EQUAL_GPC：权重全1。
- CAP：四个开发锚各自测真实DIRECT同任务容量，取两开发过程的几何平均；先用SM_PROP并发诊断的有效工作/span得到一次修正权重，**仅一次**，不得做迭代求最好分配。
- WRONG_CAP：固定循环置换CAP五个权重，真实资源绑定不变，不重新拟合。

单组容量和并发span含不同扰动，二者都保存。正式CAP用哪个阶段值在开发前写死：优先一次并发诊断修正，诊断缺失则用孤立值并标记。模型没有定位物理通信原因。

新形状使用 `plans/cases.json` 中预先指定的 `weights_from` 开发锚；本轮不再运行另一个最近邻选择器。每scope分开冻结权重。未见签名不先测速，不改该继承关系。实际长度增长用计划最大长度生成固定边界，正常token只更新原来需要的length/newKV，不重排，不从未来输入选择。

容量权重差很小、整数任务量化后与SM_PROP/EQUAL完全相同，记录alias。这不是缺bug，不能强行改变边界让CAP“看起来不同”。

## E. 最强简单基线与初始化

开发期只冻结一个BEST_SIMPLE：N19/E56_DIRECT/SM_PROP/EQUAL中完整output-ready最低者；没有后验改选。CAP是否推荐部署与这份选择分开：正式6块必须有CAP实际执行，无论开发是否推荐；正式默认仍是原N19，除非最终证据足够且用户另行决定。

初始化费用分硬件一次读数、资源创建、2过程容量校准、计划编译/图、每分配绑定。报告H=1/100/1000的代数账单并标估算。没有正稳态节省就没有有限回本点。

## F. 容量校准的准确数量与度量

四锚×五完整GPC×两scope×两个开发进程=80个孤立phase；四锚×两scope×两个开发进程=16个SM_PROP并发诊断phase，总96。

孤立测同一DIRECT完整任务集合；并发诊断每个组处理自己不重叠的SM_PROP任务范围。C_g=该组proxy工作/P阶段自身event跨度，起点在该stream执行前，不能用从全局起点累计的完成时间替代服务跨度。并发阶段额外event只用于校准/诊断，不进入正式主DAG。零或无效跨度标NA，不除零。

每scope在两个开发进程等权几何平均得到CAP，正式从此不更新。孤立容量仅是备用预测，完全没有合法并发校准时方可使用，并显式标记。正式数据能验证两种容量是否迁移，但不得回写CAP。

所有五GPC参与的CAP不保证比原生更快；实质producer分成五次发射可能付出不可忽略成本。不要用理想capacity曲线减去另一个程序的launch成本给出“预测已证明”。
