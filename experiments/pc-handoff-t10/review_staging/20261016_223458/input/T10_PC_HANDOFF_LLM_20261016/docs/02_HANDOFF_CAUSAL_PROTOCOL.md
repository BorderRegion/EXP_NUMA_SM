# P × C × W：真正的部分结果交付实验

## 1. 与旧实验的区别
旧0x33实验是预先初始化数据的消费者访问。这里每个正式epoch均运行真实数学P，覆盖全部partial W，再由C读取并完成正确输出。
`P_group`、`C_group`、`workspace allocation/offset/layout`、`schedule`、`power epoch`分别记录。
不是T10直接访问相邻SM寄存器/shared memory；路径是全局可见partial及合法同步，服务层可能涉及L2、互连或DRAM。物理归因未知时用HANDOFF_AFFINITY。

## 2. 4×4矩阵：实际LLM片段，不使用独立gather
从E1开发集按自然链中R-span占比选6例，低/中/高各2例，选择在M实现前冻结。
使用4个实际公开资源组。全组数量不预填成物理GPC；每组SM数尽量相同，T10为56时优先14×4，接口不支持则采用可实现的相同配额并记录剩余。
每例对16个P_group×C_group运行：同一A/B或Q/KV、同一split、同一workspace、同一元素顺序、同一数学kernel实例及CTA/grid配方。四组全测试，不挑数字相邻一对。
同一个cell内只用指定组做同样工作。其他组不放dummy忙等；隔离格是机制，不代表全卡服务。
同一次allocation放两个不重叠、相同大小、相同对齐的workspace槽。所有P/C组合分别使用槽0和槽1；不能用槽1的最快偏好重新命名槽0。
每槽每cell 4个轮次，顺序拉丁/随机平衡；2个开发process + 2个独立确认process（后两者不重选方向）。
上限：6例×16格×2槽×4轮×4process=3072 cell episode。每episode内部warmup与计时重复不是额外独立样本。极小cell用Graph紧密batch降timer误差，完整PC每次重算。

## 3. 计量
主量：`T_chain`=输入就绪/P提交前至C输出就绪；同一父stream合法事件对包住完整Graph，以及CPU到ready时间。
诊断：P的自然执行span、C在P后正常读取的span、依赖/launch空隙；已有profile独立采集。给C贴两个事件可能扰动微秒任务，最终计时Graph只保留外层计时，stage数来自单独诊断。
不得跨SM相减clock；P/C局部clock和%smid只在DIAG1兄弟核中使用。DIAG0真正编译掉它们和仅诊断用barrier/stores。
P-only、R-only的独立运行会改变cache与状态，只作为scope信息；两者之和与链之差不叫“纯NoC延迟”。

矩阵分析可拟合logT = mu + P主效应 + C主效应 + workspace/轮次条件 + P×C (+与W交互)。
移除主效应后的交互可以说明超出均匀组快慢，但不自动证实物理原因。
对任何提前固定的两组：
I=0.5*(log T01+log T10-log T00-log T11)。正数支持“同组”假设；负数照报，不取abs。
还需真实并发/全资源链：用两个输出tile类执行完整的任务；不能把16格的单独时间相加当并发makespan。

## 4. 输入、工作量与workspace的反事实
至少6例各做下列控制；全部在同分配、同logical任务内交错，不从历史批次相减。
A 正常P→W→C，每次更新partial。
B 相同P，换C的物理资源组，算术与访问地址不变。
C 相同P/C，换到另一个workspace基址；副本来自本轮P，不能预置正确结果。
D 相同P/C/W，P完成后扫描自有scratch再C；作为缓存状态干预，同时报告包括和不包括scratch的时间。不能称flush，不用其巨大时间稀释比值。
E 相同数学，producer任务顺序和组提交顺序正交轮换；不要让一个位置总是首先被测。

这些控制有意不声称用户不需要的完整物理映射破解。它们回答：规律跟P/C关系走，还是主要跟W/时间历史走。

## 5. 全资源桥接必须做
以E2冻结的两组，输出tile按同一owner规则分为两类，每类的全部split由同组生产。两组都做有效工作，合计原全任务。
- MATCH：每类送到预定消费者组。
- REVERSE：只互换消费者组。
- SAME_GROUP：不使用学习信息，消费者在原生产组。
全局依赖图相同，全部P完成后再放C（首轮），两组的tile数/工作配额相同；没有丢掉少数SM或少做task。
MATCH与SAME_GROUP相同就alias；不要计为两份证据。

每例至少一轮独立完整桥接，哪怕矩阵信号不到3%。该结果决定应扩大完整32shape，还是执行既定12shape阴性确认；不改研究对象。

## 6. 与屏蔽和NUMA的关系
- SM裁剪、逻辑ID相邻、资源组相同，都不是“近/远”标签的充分依据。
- 旧0x33与旧PAIR只是历史对照，不用于本轮选择producer/consumer。
- 只有稳定、真实控制的PC交互：可称执行/交付亲和。
- 有可重复的compute×address本地/远端和独立服务域证据：才考虑物理NUMA措辞。
- 即便完整链加速，也可能是workspace coalescing、融合或更好并行度；主对照必须把这些与位置信息分开。
- 没有同芯片可控屏蔽反事实/独立结构依据，不能把任何差异因果归为floorsweeping。
