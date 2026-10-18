# 内核、工作量和计时的精确定义

## 1. 一个物理地址坐标，不随结论改名

r=0..63 是本进程数据布局中的虚拟 region；k=0..rw-1 是 region 内 word。固定：

```
word_index(r,k) = (((k >> 10) * 64 + r) << 10) + (k & 1023)
physical_pointer = active_base + 4 * word_index(r,k)
D(r) = parity(r & 0x33) XOR scope_bias
```

2MiB：rw=8192，每 region 32KiB，由8个4KiB条带组成。
32MiB：rw=131072，每 region 512KiB，由128个4KiB条带组成。
它们是实际完整消费集合，不是只分配没读。四格中每个 CELL 消费半个集合；JOINT消费全体。

每 CTA 128线程，k按lane+128*j递增；输入 uint32、输出uint64精确和。数据运行时初始化，volatile `.cg` load 保留，禁止变成编译期常数。CPU按逻辑region/k顺序独立求和；不得仅复制GPU访问遍历。

class内第 j 项（0..31）的 region：
```
u = j << 1
r = u | (parity(u & 0x33) XOR bias XOR d)
```
因为最低设置位是bit0，这个式子完整覆盖一类32个region且无重复。不需要 per-task/domain 查表。

## 2. 并发与重复必须独立

L8/L1/H1 每组固定处理同一类32个region。jobs=32*visits。CTA循环 `pos=blockIdx.x; pos<jobs; pos+=gridDim.x`。两组不争抢队列。

在给定测量轮次，使用相同的预定奇数a和b：
`job=(a*pos+b)&(jobs-1)`；`j=job&31`；`visit=job>>5`。
参数只改变完整任务位置，**不改变region内部word次序**。a/b在所有四格和两个joint里一致，不由计时选择。CPU先验证其双射。

L8把每个region完整读8个独立visit；每visit输出独立槽，不把8份工作伪装成同一份。L1/H1仅一次；所以L8/L1差异混有复用和重复工作量，按匹配同profile的四格/反向比较解释，不直接相减叫NUMA时延。

每visit结束后仍需CTA barrier，避免下一任务覆盖前次归约shared存储。线程不因边界提前return跨barrier；所有参与线程迭代同一任务数。没有跨CTA自旋、全局barrier或任务领取原子。

## 3. DIAG必须在编译期删除

`reference/consumer.cuh` 是建议骨架，尚未CUDA编译；Codex本地资格后使用或在已有源码中等价实现。

- `DIAG=1`：读取SM/clock，输出region、visit、位置与有限时序，用于资格/观察扰动。
- `DIAG=0`：不能存在SM/clock读取、record写入或只有计时才需要的begin barrier。归约和下一visit安全所需barrier保留。
- 所有正式数值输出依然存在。无诊断不等于不检查正确性：资格与phase末完整读回继续做。
- 同一DIAG编译版本内，match/reverse/CELL只改scalar，不换binary。DIAG1/0两个优化产物的差异正是待研究因素，不能强求相同寄存器或插入dummy操作掩盖它。
- 保存编译命令、source/cubin hash、相关完整SASS/资源统计；静态出现次数不当成动态执行计数。

S2/S3优先只有class消费者、DIAG0；S4额外使用native全region实例与着色输出模式。除明示M布局外，out[64*visit+r]保持不变。

## 4. 四格与并发反向

```
C0D0: 只在C0读取D0
C0D1: 只在C0读取D1
C1D0: 只在C1读取D0
C1D1: 只在C1读取D1
J_MATCH: C0读D0，同时C1读D1
J_REVERSE: C0读D1，同时C1读D0
```
CELL期间不在另一组人为运行dummy任务。CELL与JOINT不是相同竞争场景，单独分析。

`I_cell = 0.5*(log T01+log T10-log T00-log T11)`；正值支持事先命名的对角匹配。
`I_joint = log(T_reverse/T_match)`；正值支持match的实际并发完成优势。
不取abs、不按测试结果重新命名D0/D1。计算行列主效应能控制其乘法尺度均值，不能自动消除缓存/功耗/顺序混杂。

同一动作重复中，各组kernel先全部提交，parent stream等全部完成后统一计时终点。跨context event不得直接做elapsed；复用已有合法parent Graph fork/join。不能把max(group_event)当完整makespan，不能把单组时间加总当并发。

PAIR4SM仅是4SM经验组机制，不与全56SM原生比较做部署收益。部署基线只在FULL scope的S4。

## 5. Primer怎么执行

S2 COMMON_PRIME：由固定primary全设备sweep读完整active数据；所有策略相同程序/网格/数据量；不是保证缓存完全相同，只是固定准备配方。
S3 OWNER_C0/1：由指定组读整个集合，程序和逻辑工作相同，仅执行资源不同；须结束后再启动消费者。
SCRATCH：primary扫描128MiB自有独立缓冲，名称为干预，不能写“已flush L2”。

每个测量epoch都执行对应primer，不能只在phase开始prime一次然后把后127次叫同样干预。把primer接入预建Graph依赖或已有合法stream，不每次用CPU同步制造额外间隔。timer起点在primer完成之后的parent依赖上，终点在所有consumer完成之后；同时保留含primer的CPU-ready与GPU span。**主I_cell/I_joint用consumer span；准备总时间另列。**

warmup执行与正式完全相同的primer+consumer配方，至少32epochs且100ms。S4 HOT没有人工primer；按同policy正常热身，不与COMMON_PRIME混池。

同一buffer内容在一个profile的6动作间不变。上传、Graph更新、重布局只能在phase或profile前完成并明确计费，不能成为某个动作免费独享的cache初始化。

## 6. 三种坐标反事实不能混用

- PAYLOAD_SWAP：在固定phi(r,k)中写value(r XOR 1,k)。D(r)和所有load地址不变；CPU期望改变。它检查内容敏感性，不是把物理数据位置互换。
- RELABEL：仅令r'=r XOR1用于逻辑命名，真正load仍回到phi(r' XOR1,k)。补偿关系 `parity(r'&0x33) XOR 1 XOR bias = D(r)`；记录原始physical_region和alias_label。主D0/D1仍沿用原物理类名，不能用未经补偿的名义符号解释反转。
- OFFSET128：在同一owned大分配内active_base改为base+128B，输入与scratch不重叠；数据量与算法不变。实际地址变了，所以失效说明冻结虚拟规则不具平移不变性，不足以否定低层地址hash。

RELABEL只在CPU重新标注同一组原始物理样本、验证补偿关系，不新增同义GPU计时；不能制造第二份独立证据。其余两种情况各自独立，不同时修改多项。新scope或后续重新分配绝不读取旧指针。

## 7. 计时与采样

S2/S3每phase至少128个consumer测量，输出的复制检查只在phase末，全部方法同等处理；结果平均以process/block为独立单位。保存每epoch数值，不每epoch打印/flush/写图。

小kernel CUDA event存在分辨率/插入成本：记录实际范围，不能由sub-tick单样本给出精确延迟。报告原始格值、重复分布和区间；不能把128epochs当128个独立器件。

S4每phase128次output-ready请求，另有同policy紧密重放batch。batch次数在单独开发N上按20–100ms目标冻结到128..8192，所有policy相同；这是重放次数，**不能改consumer的inner_repeat来凑时间**。batch与单请求不是同一主指标；不把batch均摊当服务p99。

保存parent总consumer event，CPU-ready，primer时长，graph节点数和必要init成本。每个DIAG0的首末资格由DIAG1 sibling在独立运行完成，定位证据是共享context/参数绑定及前后诊断，不声称观测了每次正式的物理位置。

## 8. 原则

这轮允许诊断实验存在primer和小probe，因为研究目标是辨识机制；正式S4不增加小调度kernel。数学结果正确与放置证据是不同检查，各做有限核对。不能把诊断store移到别的未计时kernel后宣称总生产开销消失。
