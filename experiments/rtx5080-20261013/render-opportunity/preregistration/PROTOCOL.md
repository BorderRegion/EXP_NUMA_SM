# GPU 访存亲和性 campaign 预注册

冻结日期：2026-10-13（Asia/Shanghai）。适用任务：CODEX_MASTER_TASK v1.0。
本文件在任何 GPU kernel 测量及 CPU 仿真检查之前建立。硬件盘点不计为亲和测量。
本轮 GPU 为 RTX 5080；任何芯片内结构、SM 数、L2 容量、域数仍待合法查询与测量。
冻结补充：首次CPU自检后、任何硬件测量前，明确session的算术平均帧时间口径，
修正CPU工具原先使用session中位数的实现，追加偏斜帧时间断言；阈值/seed/策略不变。
旧版工具与raw保留，见COUNTEREXAMPLES_AND_NEGATIVES.md。

## 授权与停止规则

仅本机、离线、已有资源、额外付费 0。不得下载安装、remote Git、SSH、改驱动、
MIG、防护或设备权限，不停止别人的作业。只读主机盘点的沙箱外审批不授权安装。
单 GPU worker，其他 campaign 不启动。GPU 为桌面使用，记录非独占。
若缺 CUDA 编译器或 NVIDIA CUDA headers，E1 停在资源门，不用 Vulkan 替代。
资源缺失完成 CPU 整理和 E6，状态 BLOCKED_LOCAL_RESOURCE；不把它判作阴性。
GPU device lost / OS recovery 立即终止 GPU 分支；CPU 整理继续。

## 固定预算和探测空间

E1≤1h，E2≤1.5h，E3≤1.5h，E4≤2h，E5≤4h，预留≤2h；总 GPU worker≤12h。
CPU 工具开发和分析单列。普通诊断 kernel 目标≤20ms；必须先用最短链测试并逐步扩量，
超时主动缩小，不能靠进程 timeout 保护 GPU。persistent work 有界，不等待未调度组。
缓冲区≤min(512MiB, 当前 freeVRAM 的10%)，应用余量≥max(1GiB, 可用容量的15%)。
盘点 freeVRAM 只是瞬时值，正式分配前必须重查；不得占位制造瓶颈。
工作集为查询/实测 L2 的0.25/0.75/1.5/4倍；不能查询 L2 则不猜测大小或声称 DRAM 已测。
位置与地址区段候选总数最多128，至少32个有效位置×地址单元才能拟合。
smid 使用实际稀疏标识，禁止 smid%2。未覆盖保留 missing，不填造观测。

固定主 seed=20261013；地址布局 seed=20261014；采样顺序=20261015；
CPU 置乱=20261016；块 bootstrap=20261017；策略顺序=20261018。
地址是本进程申请缓冲区的相对偏移；禁止物理页公式、地址扫描和跨进程访问。
随机非恒定初始化；生成数据的版本/seed/checksum写 manifest。

## E1：输入、缓存条件与统计

ordinary load 和工具链支持的 L1-bypass 分开，warm/primed 与 streamed 分开。
clock64 只作同次同 SM 前后差；短数据依赖链、checksum、起止 smid 均记录。
全零压缩数据不作为一般访存工作负载。保存编译配方、PTX/SASS（可得时）。
按 dispatch 先形成单元中位数，再按校准/留出运行形成 L[s,r]。
每有效单元校准与验证各至少8个独立 dispatch；两 split 的 run_id 必须不相交。
checksum失败使该输入失去资格；迁移样本单列，迁移比例>5%则地图资格未解决。
每张地图绑定 GPU UUID、driver、process/context、allocation generation、base/range、
缓存条件、load类型、workset。跨条件/分配不混池。

先拟合 mu+alpha[sm]+beta[region]，再比较实测单元残差表在同分配留出上的预测能力。
不预设两域，不把单元表命名为 GPC/NUMA；允许只有一组、任意经验交互，无强制聚类。
CPU 初始分析工具只支持同一地图已见地址的留出运行；新地址/新分配不能套用旧表。
新地址外推必须另有校准之外的资源特征或独立机制验证，目前工具未实现这项证明。
完整复验必须≥3个新进程各1个新 allocation epoch，并有同分配复测与新地址验证。
各 epoch 重新建图，检验有用性，禁止要求虚拟地址标签跨 epoch 不变。

对齐每地址的相对快慢变化，排除单纯 SM 或地址偏差。初始有用性门槛：
校准选出的快/慢位置在验证中的、扣除 SM 主效应后的差异中位数≥10%，
且≥2×验证 dispatch 相对 robust noise；交互验证 RMSE 至少改善10%；
199次固定 SM 标签置乱只置乱交互项、保留 additive 主效应，p≤0.05。
初始 CPU 置乱需要同 split 的完整交叉矩阵；缺单元则只给描述，资格未解决。
吞吐路线独立门槛5%，目前未测。较小可信差异可报告，不自动启动应用改造。
CPU 合成通过仅验证分析器，绝非硬件亲和性证据。

E1 分支：采样/诊断不足→TOPOLOGY_UNRESOLVED；充分测量无有用交互→
NO_ACTIONABLE_AFFINITY_ON_THIS_GPU；有稳定交互但控制缺失→
SIGNAL_PRESENT_CONTROL_UNAVAILABLE；交互、独立复验和潜在控制俱全才进 E2。
资源门状态优先于以上科学分支；不能让软件自动从单地图信号批准 E2。

## E2与正确性门

四方法：普通执行；相同 bounded queue 拓扑盲；正确地图；固定置乱地图。
至少5个独立进程块、平衡顺序、实际 SM 分配、队列开销、吞吐、尾部记录。
相同任务多重集合、字节数、计算量、唯一输出；每任务恰好一次，独立 CPU 整数模型。
队列消费者前构建，空队列可偷取，位置改变安全回退，不假设一 block 一 SM。
若人为限 residency，去拓扑对照使用相同约束，并计入正式成本。
无并发净收益不进入 renderer 改造。最多两次有证据的局部工程修复。

## E3–E5：应用选择和冻结

只选一个现有 CUDA renderer。先检查 CUDA 3DGS；缺少则最多检查两份现有
post-hit 队列实现，不新写 vkrt renderer、不新训练模型。现状没有候选。
资产选择规则：符合源码输出资格与显存余量的资产按规范绝对路径字典序取前两份，
先固定分辨率，再跑任何性能校准。若仅一份则报告缩小矩阵。
必须在恢复时记录实际 asset hash、camera/calibration/test轨迹 hash 与分辨率；
本轮只有空 slot，不能把空 slot 当已选择场景或已运行测试。
每场景一校准轨迹、两条真实测试轨迹（慢/快），固定 simulation/camera time。
最多8策略 B0/B1/B2/B3/B4/B5/M/C：原生、盲queue、普通局部性、仅负载、
静态亲和、共享分组+均衡、唯一联合方法、M的固定置乱消融。
所有 B2–B5 使用同等有限校准预算；最强 B1–B5 只在校准集按几何平均帧时间选择。
M/B1–B5/C 用同 binary task evaluator，native B0 另作执行组织资格对齐。
保持 tile 内 Gaussian/alpha 遍历顺序、精度、阈值、early termination，
logical pixel 输出，完整 raw 有效字段默认位级一致。未来实际访存不得作为当前特征。
post-hit random 维度绑定 logical path/sample，不绑定 queue slot。
原生数据布局为主，不增加复制/重排；无充分资源和预注册不扩大方法。

最多2场景×2轨迹×8策略×5进程块=160 session；每 session 256 warmup+512 measurement。
策略顺序由固定seed生成的旋转表事先写入 SESSION_ORDER.json；在20个case-block中
每策略每位置出现2或3次。5次单case无法完全平衡8位置，此限制必须保留。
所有策略共享每块分配对象，各自 reset/output；实际 producer 每帧正常执行。
帧是相关观测；session使用全部measurement帧的算术均值，process block是配对与 bootstrap 单位，场景/轨迹等权。
同时报告 M对校准最强基线、B0及全部其他基线，不按测试赢家重选。
端到端直接测 critical path，包含 producer、特征、标定验证、分组、queue、copy/sync。
生命周期 N=1/100/1000，仅在实测范围支持时计算；512帧不能自动外推1000帧。
break-even 只在实测 net saving>0 时定义。计数未知记UNKNOWN，remote bytes仅proxy。
p95/p99探索性；仅平均主目标有独立正信号才以原冻结配置延长，不按tail重选。

## E6与贡献边界

GO 需亲和交互→合法控制→真实应用→强基线增量→拓扑消融→完整成本→新增问题。
约5%帧改善是追加投入参考，不是投稿保证。只有 CPU/微测试不构成渲染 GO。
SOURCES_AND_SCOPE.md 及论文正文目前缺失：相关工作名字只来自任务书，
不得编造文献结论或宣称新颖性，最终标明哪些比较尚未核验。
最终交付主报告、贡献卡、差异卡、环境/资源表、raw/derived、预算和导师短稿。
