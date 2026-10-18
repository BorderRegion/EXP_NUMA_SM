# 测量、统计与完整成本

## 1. 计划规模（每平台条件式上限）
| 矩阵 | 规模 | 最大phase/session数 |
|---|---|---:|
| 主grouped测试 | 72case×6独立块×(6策略+2锚) | 3456 |
| Attention decode测试 | 32case×6块×(4策略+2锚) | 1152 |
| 完整MoE层四格+库 | 18case×6块×(5策略+2锚) | 756 |
| 小型launch/fusion诊断 | 12case×6块×4格 | 288 |
| 真实trace补充（可用时） | 最多12序列×6块×4策略 | 288 |
| 全模型（可用时） | 2模型×3profile×3块×(3策略+2锚) | 90 |

开发集、qualification、dense/prefill/异质K控制另记，受相应阶段worker总预算。上述不是必须全跑的KPI，不能越预算补格。
Grouped弱信号分支：预注册72测试case中按(K,N/E/R/分布)层级等额固定24个，不按性能挑选，6块×8phase=1152。完整层则固定6测试case×6块×7phase=252。attention始终尽量完成32个支持case的有限比较，若adapter不存在则baseline/缺项。
自本包之日起不引用旧phase数量作为新GPU结果。

## 2. 生产路径而非审计路径
资格和正式使用相同数学binary、资源布局、meta生命周期、graph/eager模式、warmup方法。不要短sample重审计PASS，正式却换长路径与不同reset。
正常计时不每iteration写SM号、不每kernel CPU同步、不逐条落盘、不每帧hash大张量。必要正确性使用资格、batch末完整结果和预选首中末样本；异常才有限诊断。

## 3. 三种时间不能混用
- `device_interval_ms`：同一context、同一stream依赖范围内的CUDA events。若包括host等待缝隙，标GPU_TIME_SPAN，不叫busy。
- `operator_or_layer_ready_ms`：调用入口至可用输出，包含必要hostplan/metadata/dispatch/clone/merge。
- `worker_occupied_s`：该worker从获锁到GPU实验任务及必要准备释放，包含编译、初始化和IO等待；是预算口径。

不将不同context的event相减，不将max(group_time)当完整makespan。主路线没有新增Green，但工具层仍应拒绝这类错误汇总。

## 4. 运行方式
先根据baseline开发点决定每组重复次数，所有策略使用同一replay长度。
- 每策略热身至少64次且至少0.3s的实际路径，常规上限256次；若256次仍不足0.3s，可延长有用热身至0.3s，不重复编译。
- 每phase至少128次测量，最多512次；用baseline时长预先确定，使aggregate约50–200ms，可按预算缩短并披露。
- 单算子steady：一个范围内连续发射/Graph replay，末端一次同步；计算amortized mean。不要把batched mean的重复值当每请求p99。
- 动态shape/route：每个重复使用预先独立的有效输入项，执行必要descriptor更新；固定ring长度≥16。不能candidate独享热输入。
- 层请求延迟：每请求在真实需要的结果边界同步，序列内部不逐kernel同步；candidate与baseline同样的输入供应和同样的结束点。

想测每请求p95/p99，另用固定的长请求序列真实逐请求记录，不用均值乘除推tail。本轮512或更少条的p99仅探索性，不作SLO保证。只在两平台局部真实增量明确时，用阶段预留对最多2profile扩到2048请求；规则事前固定。

## 5. 顺序和漂移
每case 6个独立进程块。六策略用固定Williams/平衡排列；块首尾各LIB锚。主LIB本身仍位于平衡序列内。
四格/五策略矩阵用固定轮换与反向，不冒称6轮就完全抵消所有carryover。记录实际phase开始/结束，低频温度、时钟、power和throttle reason（可读时）。
若首尾锚差>5%，不静默剔除或按温度回归“修正”。报告原始配对与首尾敏感性；若主要结论在锚选择下翻转，标 `DRIFT_LIMITED`。允许阶段内至多一次预先指定的相同输入短确认，不反复取最好时间。不锁频、不改功耗以找正数。

## 6. 统计单位
独立单位是process/input-sequence block；tile、element、连续replay不是独立实验。先算每block各phase mean，再算candidate/reference log ratio；跨case分组报告，再按预定形状/来源等权汇总。
bootstrap按process block（必要时sequence family）重采样20,000次，固定seed；数据点太少时给原值和范围，不能用百万个元素制造窄区间。
主比较：FULL对LIB，以及FULL对开发集冻结的同融合强简单策略。两主比较报告Holm校正或同时区间；其余探索性。
T10和5070Ti分别统计，不混原始毫秒数。跨平台只并列相同合同/shape的相对效应和支持矩阵；不同backend版本/方法patch分层，不暗中合并。

## 7. 必须拆出的成本
一次性：模型加载、weights pack、JIT/AOT、autotune、Graph capture、静态规则生成。
每step：router、count/scan、pack、meta更新、kernel内部scheduler、mainloop、activation/merge、copy/consume。
有些内部scheduler成本不能独立计时：可做same-body q=1/固定q/完整q消融、编译指令与少量trace；写estimated/unknown，不在mainloop中不断clock采样来制造新瓶颈。

## 8. 为什么没有收益也要有数据回答
顺序检查：
A. LIB vs CORE：数学主体是否已经落后？
B. CORE vs BAL/CACHE/FULL：同体调度有没有差别？
C. F1S0 vs F1S1：同样fusion后新策略还有价值吗？
D. OP_RESIDENT vs PRODUCER_CONSUMER：是否把准备成本留在计时外？
E. kernel vs layer/model：目标占比、其他模块、串行依赖限制有多大？
F. 稳态 vs cold/startup：是否只能长时间重复回本？

不依据一个slow kernel或一个未融合prototype宣布所有亲和无效。另一方面，也不将一个fusion赢幅重复算成scheduler赢幅。

## 9. 必交图表
1. 原生及候选DAG与实际launch/copy/wait计数。
2. 各类shape在LIB上的时间和有效FLOPs/逻辑字节；指标明确不是实际DRAM流量。
3. grouped/attention shape热图与完整负例，不只最大加速。
4. 六策略配对图，平台分开。
5. fusion×schedule四格与交互。
6. producer/metadata/compute/merge完整成本绝对ms及比例。
7. 输出tile、packet与估计/可测尾部；没有native计数不伪造。
8. 独立trace、冷暖/不同层权重、真实模型适用矩阵。
9. 数值质量、路由保持、NA/失败/缺资源。
10. 初始化摊销与预算；没有净正均值时回本为不存在/未建立，不画虚假交点。

有数据才画；CPU工具的虚构示例不进入论文图表。使用本地已有绘图库，无需联网装新包。
