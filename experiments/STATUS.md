# 最新：2026-10-18 新固定基线与低成本真实核采样确认完成

目录 `topology-real-t10`，运行 `20261018T123848Z`。按用户要求把上轮约+0.68%的规则54（offset17/page17/RND07）作为两条件的新BASE，正式GPU二进制逐字节保留。另保留旧同TPC规则LEGACY11、上轮条件特定FROZEN54/56、新开发STATIC、错误/混合/影子分配以及同参数A/A对照。

新基线复验：BASE54相对LEGACY11热输入+0.8318%，95%区间[+0.7628,+0.8976]；逐次重写输入+0.3346%，区间[+0.2269,+0.4276]，均6/6正。默认继续保留54。这是固定规则收益，不宣称地址感知成功。

新方法16候选=4flags偏移×4配对家族，固定邮箱页17。CPU批量采样真实原核，先筛选，再对前三名和BASE做两轮精炼；两轮均正且几何速度比>0.15%才改变选择。每次58Graph/1,856个完整算子，包含预热、更新和最终安装。2开发进程冻结STATIC为batch12、freshbatch45；6确认进程、11对照、每条件每方案每进程1,048,576请求，完整收费。

主结果：TUNED相对BASE热输入−0.2728%，99.75%区间[−0.4399,−0.1333]；重写输入−0.2563%，区间[−0.3440,−0.1513]，两者0/6净正。热输入6/6退回BASE，未扣校准−0.0043%；重写输入3/6改变选择、3/6回退，未扣校准−0.0087%。准备中位17.563ms与25.933ms。不是单纯延长摊销就可兑现的正毛收益；尚未达到地址亲和净加速目标。

所有正结果保留：热输入TUNED比新STATIC快+0.6289%，但STATIC自身比BASE慢−0.8960%；不能据此称成功。freshbatch STATIC相对BASE+0.0634%，5/6正，仅次要静态调参结果。TUNED同参数A/A分别+0.0099%、+0.0216%，95%区间均含零。PLACE_ONLY亦未胜BASE。全部20主对比、262144请求前缀、各口径和逐进程结果均已归档，无删点、换参或GPU补跑。

诊断：真实核低预算筛选与独立短测的Pearson为+0.586、−0.186、−0.516、+0.819，仍有明显状态/节奏依赖，不能把真实核采样自动视为可靠预测。BASE的28对包含1同TPC、7同GPC不同TPC、20跨GPC；原核SM0–15各2432元素，其余各2304元素。配对收益可能受不均衡到达影响，地址偏移也同时移动邮箱/控制行，尚未独立识别裸SM通信机制。

12个GPU worker全部完成，共1241.284/2400 worker秒；1,338数值检查、16张Graph、32输入哈希核验通过；40次含资格/影子校准74,240算子；短测26,240条，长测138,412,032正式请求+135,168预热请求。统计单位为6进程。62–80°C，100W与保护保持，当前无后台GPU实验。memcheck/synccheck资格通过，racecheck仅原paired1次定点launch，无新GPU代码。

GPU全部完成后首次CPU汇总因NumPy布尔值JSON序列化失败。冻结analyze.py未改，独立analyze_repaired.py只转换输出标量类型，公式/选择/原始数据不变；原错误日志和修复记录保留。完整包通过CRC/逐文件SHA256、独立解压纯CPU重算18派生文件及复算后哈希核验。

下一步待验证方向：将采样嵌入实际请求流，计入探索损失与参数更新、对齐采样/长测节奏，减少额外算子调用；保持同预算静态/错误地址/影子对照。若仍无改善，换通信占比更高且工作区长期复用的LLM部件。不得将重复搜索直到出现正数当作达成目标。

报告：[REPORT.md](/home/ubuntu/文档/ChatGPT/numa_gpu/topology-real-t10/reports/REPORT.md)。交付：[DELIVERY_INDEX.md](/home/ubuntu/文档/ChatGPT/numa_gpu/topology-real-t10/reports/DELIVERY_INDEX.md)。完整包2683项/26,951,078字节，小包68项/789,300字节；完整SHA256 `b5832e8e167af86124f2106f89cd42fd255f8dca87002dd57f68765e22f385e6`。

完整包：[ZIP](/home/ubuntu/下载/T10_REAL_KERNEL_AFFINITY_20261018.zip)；网页版GPT小包：[SMALL ZIP](/home/ubuntu/下载/T10_REAL_KERNEL_AFFINITY_20261018_SMALL.zip)。

以下为历史记录：

---

# 最新：2026-10-18 完整通信尾部/地址放置实验完成，代理选择未带来NUMA净加速

新目录 `topology-tail-t10`，运行 `20261018T084714Z`。正式原softmax_const.so保持逐字节相同，新增完整配对/28路归并/广播代理微测；12种flags/邮箱放置×11种配对共132候选。2开发进程冻结静态BLIND，6确认进程分别检验PAIR_ONLY、PLACE_ONLY、JOINT及错误/混合/独立分配/同参数对照。每方案/条件/进程1,048,576请求，本轮外层账单明确包含全部参数更新和conditioning。

主要结果：JOINT热输入相对原快核−0.360%，99.6875%区间[−0.628,−0.032]；相对BLIND−1.029%，6/6负。逐次重写输入相对原快核+0.274%，但只有1/6为正，区间[−0.823,+2.926]；相对BLIND−0.799%，6/6负。16个预定义主对比未建立地址亲和净收益；PLACE_ONLY亦未过门槛。原默认配对未替换。

freshbatch的小正平均由confirm_2的+4.535%拉起，其余五进程均负。该进程原配对有GPU event约0.309ms、host约99.164ms的长尾，也有GPU本身长尾；没有系统调度追踪，具体原因未知。所有观测原样计入主结果，无删点/补跑。辅助GPU口径JOINT相对原配对−0.593%，6/6负。全108条件的事后尾部检查在TIMING_TAILS.json，明确标注事后描述性分析。

可保留的新强对照：BLIND静态规则热输入+0.677%，95%区间[+0.553,+0.786]，6/6正；候选54=offset17/page17/RND07。freshbatch静态候选56=offset17/page257/SAME_GPC，外层+1.081%被长尾放大，GPU口径+0.216%，6/6正。离线开发26.266worker秒不计在线费，不能称为地址感知因果收益；建议作为下一轮强基线而非当前NUMA成功。JOINT同参数A/A热输入+0.064%，95%区间未含零，仍有小偏差。

诊断：完整尾部留出成本与开发集真实132候选算子时间的Pearson仅−0.158至+0.142，排序预测弱。代理只thread0读广播结果、正式核整个CTA读且输出，真实缓存/流水线状态及屏障到达未完全重现。准备中位热输入30.605ms、重写输入47.354ms。下一步优先少量实际原核采样+冻结选择/等采样预算盲选对照，或通信占比更高且工作区复用的LLM部件；不能以一直搜索到正数替代验证。

16个worker记录，13完成；初期2个host资格失败及1个中断的全量racecheck全部保留。实测已知1078.124秒+中断保守预算记账240秒=1318.124/2400预算秒，中断真实结束时刻未知。新tail单launch定点racecheck通过，不宣称全量racecheck通过；memcheck/synccheck资格检查通过。5,613数值检查、67,584微测launch、16张Graph、32个输入哈希核验；长测113,246,208正式请求+110,592预热请求，统计单位6进程。62–80°C，100W及保护保持。当前GPU实验已退出。

报告：[REPORT.md](/home/ubuntu/文档/ChatGPT/numa_gpu/topology-tail-t10/reports/REPORT.md)。交付：[DELIVERY_INDEX.md](/home/ubuntu/文档/ChatGPT/numa_gpu/topology-tail-t10/reports/DELIVERY_INDEX.md)。完整包2477项/34,011,454字节，小包97项/741,649字节；CRC/逐文件SHA256、独立解压纯CPU重算15派生文件和复算后哈希全部通过。完整SHA256 `7ca23081e4d5810b3c73bf27c4103eb42d54b1be76b8e94340e8a05ec8c1781f`。

完整包：[ZIP](/home/ubuntu/下载/T10_TOPOLOGY_TAIL_PLACEMENT_20261018.zip)；网页版GPT小包：[SMALL ZIP](/home/ubuntu/下载/T10_TOPOLOGY_TAIL_PLACEMENT_20261018_SMALL.zip)。

以下为历史记录：

---

# 最新：2026-10-18 真实拓扑与同分配地址调度实验完成

真实分组比较完成：56×55有向SM对、三页、两轮、六独立进程。页17孤立邮箱往返均值同TPC1160.6ns，同GPC不同TPC1178.9ns，跨GPC1174.3ns；同TPC小幅优势不等于裸连线延迟。原固定配对28对已经全部同TPC。并发28对时局部性偏好可反转，当前没有建立稳定GPC NUMA域。

原softmax_const.so逐字节保留，仅更新224字节配对参数。主实验、共用Graph复验、低开销并发校准复验均保留。同allocation校准中位37.37ms；每方案每进程1,048,576次完整请求的热输入净速度比相对原配对+0.418%，99.375%区间[+0.048,+0.775]，5/6正，但相对冻结随机、错误地址、混合地址分别−0.323%、−0.339%、−0.625%。每次重写输入时相对原配对−0.214%，区间跨零。尚未达到地址亲和本身的稳定净加速门槛，默认配对未替换。

净账单口径为实测请求块外层墙钟+候选完整校准+全部参数更新，对照免准备费；不含共同Graph创建、块间研究落盘及conditioning，不能称整模型端到端提速。原主实验页17重写后连续调用−1.705%等负结果完整保留，不被补充实验替换。

34个GPU worker全部完成，1343.162/3600 worker秒；25,904数值检查、2352Graph检查通过。常规阶段1,517,184条计时记录，长测试62,914,560次算子请求；统计独立单位仍为6进程。100W及保护保持，63–79°C。当前无后台GPU实验。CPU依赖/编译/新格式分析修复及原失败日志均保留。

完整包2605项、小包94项通过CRC和逐文件SHA256；完整包独立解压纯CPU复算35个派生文件并核验复算后哈希不变。完整包SHA256：`5e3eaf9f379b07b360ad654af2b039b2112049b1a994522e9188f85b2bd273a2`。

报告：[REPORT.md](/home/ubuntu/文档/ChatGPT/numa_gpu/topology-affinity-t10/reports/REPORT.md)。交付：[DELIVERY_INDEX.md](/home/ubuntu/文档/ChatGPT/numa_gpu/topology-affinity-t10/reports/DELIVERY_INDEX.md)。完整包：[ZIP](/home/ubuntu/下载/T10_TRUE_TOPOLOGY_AFFINITY_20261018.zip)；网页版GPT评审小包：[SMALL ZIP](/home/ubuntu/下载/T10_TRUE_TOPOLOGY_AFFINITY_20261018_SMALL.zip)。

以下为历史记录：

---

# 最新：2026-10-18 本机 T10 的物理 GPC 屏蔽分布已直接确认

使用 NVIDIA 580.178.04 官方同版本 RM GET 接口，三次独立进程读取一致；物理 GPC 0–5 启用 SM 数为 **10、12、12、10、0、12**，不是逐 GPC 均匀屏蔽。GPC 掩码 0x2f；TPC 掩码分别 0x3e、0x3f、0x3f、0x1f、0、0x3f。物理 GPC4 整组关闭，GPC0/TPC0 与 GPC3/TPC5 各关闭两 SM，共56/72 SM启用。

逻辑→物理 GPC 映射直接读为0→0、1→1、2→2、3→3、4→5；逐SM映射、每TPC两SM、CUDA56SM交叉一致。可选GR_GET_PHYS_GPC_MASK接口返回权限不足，未用其输出；其余用于结论的查询全部成功。没有改驱动、屏蔽、时钟、100W功耗或保护。

旧IDENTITY相邻偶数/奇数SM固定配对28/28均属同TPC；旧页17 MINIMAX为5对同TPC、1对同GPC不同TPC、22对跨GPC。这里只分类旧配对，不重写旧性能结论。非均匀配置不等于已证明NUMA延迟或净加速；GPC编号也不是平面坐标。下一步有条件按真实同TPC/同GPC/跨GPC分层，而不再用延迟聚类代替硬件分组。

报告：[REPORT.md](/home/ubuntu/文档/ChatGPT/numa_gpu/gpc-mask-t10/reports/REPORT.md)。完整映射：[SM_TO_GPC_TPC.csv](/home/ubuntu/文档/ChatGPT/numa_gpu/gpc-mask-t10/reports/SM_TO_GPC_TPC.csv)。本次无新GPU性能实验，无后台实验任务。

以下为历史记录：

---

# 最新：2026-10-18 均衡工作与固定归并者复验完成，NUMA净加速仍未达成

独立新运行 `20261018T050207Z`，保留原快核。完成OLD/BAL/FIX/BOTH四变体、131072词表与129024完全均分控制、热输入/重写输入/32次连续/重写后连续四种运行条件；BOTH另外检查地址页0、257。两开发进程选出每条件最强随机映射，确认前冻结；六确认进程不再改配方。

主条件131072、预选页17、均衡且固定SM1归并：MINIMAX相对同内核固定配对，热输入−0.172%，重写输入−0.963%，连续运行+0.628%，重写后连续+0.208%。16项预定义地址对照没有通过保守区间判定；相对原快核固定配对，完整新内核在四条件均慢2.801%–4.282%。原快核未替换，不将普通融合收益算为NUMA。

重要诊断：指令和映射相同但编译入口/Graph不同的对照，热输入差+0.835%，重写后连续差−0.835%；这不是严格同一二进制A/A，来源未隔离，不称为纯计时噪声。块间CPU处理/落盘后的首次调用与连续后续调用也不同。仅看后4次的事后敏感性分析仍无法让新完整内核胜过原快核。旧映射只按相对页号迁移，没有在每次新显存分配上重新校准，故不能据此否定一切地址相关性。

14个worker（13完成，首次sanitizer路径失败保留并用完整工具复验），2073.490/2400 GPU-worker秒；开发82944条、确认663552条计时；57308项数值检查和6912项Graph节点/顺序核验通过。63–69°C，100W及保护保持，无后台GPU实验。确认启动前已修正潜在种子重叠，原/新协议与时刻均保留，实际输入哈希验证独立。

完整包2637项、小包59项通过CRC/逐文件SHA256；完整包独立解压纯CPU复算通过，复算后包内文件哈希不变。下一轮的实际workspace校准、完整通信图与提交节奏控制仅记录为待验证假设，本轮未执行。

报告：[REPORT.md](/home/ubuntu/文档/ChatGPT/numa_gpu/numa-affinity-causal-t10/reports/REPORT.md)。交付：[DELIVERY_INDEX.md](/home/ubuntu/文档/ChatGPT/numa_gpu/numa-affinity-causal-t10/reports/DELIVERY_INDEX.md)。完整包SHA256：`69d90cc834ea3521c0b9b05c91f7d582e0ce7f4a701b7238c21d70ef4ef9944c`。

以下为历史记录：

---

# 最新：2026-10-18 冻结快核后的 SM 地址配对实验已交付

原 Attention 快核逐字节保留；一次领取整组页面的地址调度相对快核慢 8.918%，相对同开销盲调度慢 0.136%，未替换原实现。

在 131072 词表 Softmax、仅按训练微测预选的邮箱页 17、热输入且每次不重写条件下，同一个常量参数 kernel 只换配对，完整 GPU 时间比固定配对减少 2.157%，比 12 套随机配对几何平均减少 1.024%，比错误地址配对减少 1.403%；三项各 6/6 新进程为正，四词表修正后的 98.75% 区间均为正。这是条件性配对净效果，尚不能唯一归因于物理链路距离。

同一点在每次重写 logits 后优势不稳定，连续 32 次批量节奏相对固定配对反而慢 1.481%（98.75% 区间为负）。固定每 SM 工作但尾部工作量不均、最终归并者变化及运行节奏仍是因果缺口。未建立物理 NUMA 域或被屏蔽 SM 的几何拓扑，未达到可通用部署的 NUMA 净加速；API 默认 NATIVE，实验映射必须显式启用。普通融合收益不计为 NUMA 收益。

本轮 67 个 worker 已结束（65 个完成、2 个早期失败保留并另行修复复验），累计 3045.143/3600 GPU-worker 秒。开发计时观测 44160、独立确认/控制 1642752；58297 项数值/接口检查通过。100 W 与保护保持，采样 64–71°C，无后台 GPU 实验。源码、原始正负结果、修复记录、拓扑矩阵、实际 Graph 和接口成本均保留。

完整包 3908 项、小包 96 项的 CRC/逐文件 SHA256 通过；完整包独立解压纯 CPU 复算通过，复算后文件哈希不变。后续 GPU 实验需新协议、账本和独立数据，不修改本轮冻结映射。

报告：[REPORT.md](/home/ubuntu/文档/ChatGPT/numa_gpu/numa-affinity-fastpath-t10/reports/REPORT.md)。交付索引：[DELIVERY_INDEX.md](/home/ubuntu/文档/ChatGPT/numa_gpu/numa-affinity-fastpath-t10/reports/DELIVERY_INDEX.md)。完整包 SHA256：`1a1b52e9a96231371b84fbd18e0b5a1aa911019b556ff23630887502862aef32`。

以下为历史记录：

---

# 最新：2026-10-18 NUMA 调度思路与 GQA kernel 开销优化已交付

四组“KV 写入+Attention”完整 GPU 用时，相对开发预选较快旧实现减少 25.157%～37.800%，每组6/6新进程获益；等权几何汇总32.175%。旧无偏好队列、上一轮已有写入融合均纳入强对照。确认前冻结直接/动态选择，四案例98.75%进程bootstrap区间均为正。

正收益归于16字节KV搬运和合适的任务分配，不能归为NUMA成功。地址偏好比同机制无SM偏好队列汇总慢1.584%；反向和打乱标签控制、粗粒度及双副本负结果完整保留。最终不复制KV、不新增调度/清零kernel，GQA8写入图3→2，其他形状kernel数不变。可调用接口为 `numa-locality-scheduling-t10/src/locality_plan.py`；固定页表下建表一次，热态不分配显存。实际模型及成熟专用decode基线未完成，不声称整模型/SOTA或算法新颖性。

正式确认475200请求，开发74752请求另计；212+180资格、80任务定位、96接口检查通过。memcheck/synccheck及向量版定点racecheck通过。31项worker全部完成，1270.168/1800 GPU-worker秒；采样63–72°C，100W及保护保持，无后台实验。后续复验须新建协议和运行目录。

完整包2200项、小包100项CRC/哈希通过，独立解压纯CPU复算通过，复算后交付文件哈希不变。核验后的临时解压副本已清理以释放磁盘，原始数据和ZIP保留。

报告：[REPORT.md](/home/ubuntu/文档/ChatGPT/numa_gpu/numa-locality-scheduling-t10/reports/REPORT.md)。交付索引：[DELIVERY_INDEX.md](/home/ubuntu/文档/ChatGPT/numa_gpu/numa-locality-scheduling-t10/reports/DELIVERY_INDEX.md)。完整包SHA256：`f4e9e7943e09647ffb2f0ea79bc285fcb672f72a86abbe0a7f89a2ab09d19701`。

以下为历史记录：

---

# 最新：2026-10-17 GQA 解码 kernel 优化与 KV 写入融合已交付

完成六组尺寸的 GQA 解码 Attention 实现及强控制验证：相对开发阶段预选较快本机库，完整 GPU 用时减少 33.554%～55.323%，每组 6/6 新进程为正；主机提交至就绪汇总减少 41.636%。结果来自合成 Q/K/V 的部件实验，不是整模型 token/s，也未证明超过成熟专用 decode 实现。

地址偏好相对同队列无偏好慢 0.962%，相对最佳普通核慢 2.848%；不能归为物理 NUMA 成功。可用收益来自共享 KV、序列分片与谨慎融合。KV 写入融合以未修改原 Attention 二进制加独立写入作强控制，五组减少约 0.8%～5.6%；GQA8_LONG 的 -0.065% 区间跨零，接口默认保留原核与独立写入。不同阶段百分比不能相加。

已实现 `llm-decode-locality-t10/src/optimized_decode.py`，热态不分配显存、不作 CPU 地址拟合，接口实际捕获/数值/图结构检查 28 项通过。正式确认共 345600 次请求；所有正负、慢态与较弱基线记录保留。核心及写入版本 memcheck/synccheck 通过，核心定点 racecheck 通过；写入版本未单独全量 racecheck。长序列和批量 A/A 波动仍在，报告披露范围限制。

新账本 916.995/1800 GPU-worker 秒，27 项 worker 全部结束，100 W 与温控保护保留，无后台 GPU 实验。完整包 1674 项、小包 94 项 CRC/哈希通过；独立解压纯 CPU 复算通过，复算后全部文件哈希一致。后续 GPU 复验另建协议、目录和账本，不覆盖本轮原始数据。

报告：[REPORT.md](/home/ubuntu/文档/ChatGPT/numa_gpu/llm-decode-locality-t10/reports/REPORT.md)。交付索引：[DELIVERY_INDEX.md](/home/ubuntu/文档/ChatGPT/numa_gpu/llm-decode-locality-t10/reports/DELIVERY_INDEX.md)。完整包 SHA256：`4d0f33c075de6226af8f7c6209ecca81f9085131fc593407c8e732dc2018f3ce`。

以下为历史记录：

---

# 最新：2026-10-17 页内地址队列、融合与强 GEMM 基线复验已交付

两阶段 207360 次正式确认请求全部保留。地址队列相对原普通 GEMM 用时增加 1.278%，相对无偏好队列增加 0.234%，没有可靠地址感知净收益。R_G017 的旧配方融合两轮分别减少 1.803% / 2.120%，但在调优配方上融合反而增加 1.187%。

可复用结果：D13（48×2048×6144）调优普通 CUTLASS 相对 cuBLAS 完整 GPU 用时减少 8.616%，六进程均正；主机提交至输出就绪减少 8.336%。R_G017 调优普通相对旧版减少 16.154%，仍慢于 cuBLAS。已实现并验证形状选择接口：D13 用 recipe 0、split-K 2，其余尺寸回退 cuBLAS。收益归于配方选择，不归于 NUMA。

审计披露：两阶段各自前两个确认进程与开发复用输入种子；全六进程结果保留，按未重复种子的四进程复算 D13 仍减少 8.932%。D13 块前/块后 cuBLAS 敏感性为 9.145% / 8.442%。V13 A/A 和执行位置影响仍大，根因未关闭，不能宣称其融合收益稳定。全量 racecheck 超时明确不是通过；定点 racecheck、全量 memcheck/synccheck 通过，失败记录保留。

新账本 622.861/1800 GPU-worker 秒，100 W 与温控保护保持；无后台实验。完整包 1643 项、小包 78 项哈希与 CRC 全通过；独立解压后纯 CPU 复算通过，复算后全部文件哈希不变。

报告：[REPORT.md](/home/ubuntu/文档/ChatGPT/numa_gpu/address-gemm-v2-t10/reports/REPORT.md)。交付索引：[DELIVERY_INDEX.md](/home/ubuntu/文档/ChatGPT/numa_gpu/address-gemm-v2-t10/reports/DELIVERY_INDEX.md)。完整包 SHA256：`47275c4a43d596b2e21a5b361898cb85321fb03590681df8a408924ed5fe94f8`。

以下为历史记录：

---

# 最新：2026-10-17 地址感知调度接入真实 GEMM，实验已交付

已复用原 CUTLASS Tensor Core 乘法二进制，实现真实 split-K 中间结果的地址感知归并。六新进程、四尺寸、两 workspace 偏移、八对照，92160 次正式完整请求全部保留。ADDRESS 相对同核固定分配 GPU 时间减少 0.1795%，相对原版 CUTLASS 增加 1.9429%（0/6 进程获益），主机输出就绪增加 1.8282%；相对 cuBLAS 增加 20.3587%。R_G017 相对固定分配减少 0.3512%，相对原版增加 1.4766%。不默认启用该优化，不声称真实算子净加速或物理 NUMA。

3072 数值检查、1920 SM任务定位检查通过；边界/alpha beta资格检查、memcheck和synccheck通过。原始校准地址残差复现很弱，A/A波动全部保留。初版globaltimer断言失败和已完成部分结果保留；修复只改变校验/落盘，六个进程重新完整执行。

新增可选CPU建表加速器，全部240张已执行表逐元素一致，中位建表成本4163ms→24.90ms；这不改写GPU实验结果。独立解压CPU复算及全部manifest校验通过。独立新账本461.730/1800秒，旧账本不变；100W与温控保护保持，无后台GPU实验。

交付索引：[DELIVERY_INDEX.md](/home/ubuntu/文档/ChatGPT/numa_gpu/address-gemm-t10/reports/DELIVERY_INDEX.md)。

以下为历史记录：

---

# 最新：2026-10-17 SM拓扑与地址感知调度已交付

逐SM矩阵与调度原型完成。实测通信代价依赖SM对及缓冲地址；同址周期形状相关0.981，跨位置约0.078。固定旧地址类下自然偏好34/22SM，六进程56个SM方向一致。最终地址感知原型相对固定/随机/不看地址配对，通信事件区间分别减少2.458%/1.101%/0.478%，六新进程汇总。单条件负例保留；不声称物理连线或渲染/GEMM提速。

新授权范围单独记账2.444679/15GPU-worker分钟；上轮330分钟账本关闭且未改写。全量包580项、小包94项hash及CRC、独立解压CPU复算通过；无后台实验，100W保持。不要自动追加GPU实验。

交付索引：[DELIVERY_INDEX.md](/home/ubuntu/文档/ChatGPT/numa_gpu/sm-topology-t10/reports/DELIVERY_INDEX.md)。

以下为历史记录：

---

# 最新：2026-10-17 T10统一准备流程复验已交付

4个新正式进程完成；1Hz两块净吞吐-10.53%，20Hz两块-7.89%。旧慢态未充分复现，根因未关闭，不能认定物理NUMA。40条数值检查通过，独立解压CPU复算和204项manifest校验通过，无后台实验。

交付索引：[DELIVERY_INDEX.md](/home/ubuntu/文档/ChatGPT/numa_gpu/matched-pacing-t10/reports/DELIVERY_INDEX.md)。累计GPU-worker329.242082/330分钟；固定100W与保护保持。锁频和硬件缓存计数器仍受系统权限限制。不要自动重跑或追加GPU实验。

最终ZIP SHA-256：`42026e4e2c94ba52853a4640447c83dd2529330422836667ef59f35f2c05a2de`。

以下为历史状态记录：

---

# 最新：2026-10-17 T10运行状态诊断已交付

本轮主6块与8块辅助实验、分析、九图和独立解压CPU复算全部结束；无后台实验。主块100us间隔吞吐汇总+20.67%，辅助复验-5.95%，未达到稳定净提速；不能认定物理NUMA。固定100W保持，锁频及硬件缓存计数器权限限制仍存在。

交付索引：[DELIVERY_INDEX.md](/home/ubuntu/文档/ChatGPT/numa_gpu/state-causality-t10/reports/DELIVERY_INDEX.md)。本轮15.219121 GPU-worker分钟，累计323.953793/330分钟。最终ZIP SHA-256：`0c55d371b01676a32a521f47a463ef910c19935edaffca26d302510abf2960ac`。不要自动重跑或追加实验。

以下为历史状态记录：

---

# T10 补充实验已完成

按2026-10-15用户上传复审包完成S0–S5有界补充，GPU已释放，无后台实验。上轮数据与结论保留。

- S1：24块/120 sessions/61,440帧请求，原M/R不改，N首尾+E/R/M六排列。W1 M/N=1.10332、M/R=1.00116；W2 M/N=1.66348、M/R=0.99691。计算状态CAPACITY_RESULT_CONFIRMED。
- S2：6分配/72配置；初始实现遗漏CTA任务顺序轮换，开发3分配和首个确认仅作受限证据；后2个确认完成固定逐轮置乱。保留全部结果，不突破72配置补跑。初始高相关不作为物理地址亲和证据。
- S3：24块/144 phases/18,432 epochs。2MiB顺序访问A/I=0.94216、A/P0=0.95596、A/P1=0.94078，但A/N=1.13160。状态CAUSAL_AFFINITY_NO_NET_GAIN仅指本执行器内经验匹配作用，不证明物理NUMA。
- S4未触发；未新增渲染快照/动态A_addr，不将NOT_RUN写成负结果。5070Ti未访问。
- 67个成功进程，1个未启动GPU的队列取消；5次sanitizer均零错误；完整正确性与独立placement资格通过。实际执行时间窗不重叠。微诊断最大单段0.655488ms。
- 补充worker1664.812秒（27.75分钟），低于6小时上限；无下载、安装或驱动/功耗/时钟修改。资源租赁0元，电费未计。

入口：reports/T10_SUPPLEMENT_AND_PAPER_POSITION.md、reports/T10_EVIDENCE_ADDENDUM.md、reports/T10_SUPPLEMENT.json、reports/T10_5070TI_HANDOFF.md。

轻量审阅包：/home/ubuntu/桌面/GPU双卡拓扑实验_交付_20261014/T10_SUPPLEMENT_GPT_20261015.zip
大小5000031字节；CRC与全部入包SHA256通过。完整新raw仍保留在runs/t10/S1、S2、S3。

---

以下为原轮已完成记录：

# T10 计算拓扑实验

状态：本机授权实验、统计、报告、复现验证和最终压缩封装全部完成。截止2026-10-15 09:35 CST，按协议提前收束，不再启动GPU实验。

终态 **TOPOLOGY_OBSERVED_NO_DEPLOYABLE_GAIN**。这里仅有公开资源组/逻辑SM覆盖证据，无物理GPC或floorsweeping因果主张。

- 实测Tesla T10、cc7.5、56 SM、4 MiB L2；n_device=1，cluster NA。RTX5070Ti未在本机运行。
- E2 144、E3 252、E4 48进程块/144策略session全部完成；73,728条正式帧/请求。
- W1 M/N=1.11128、M/R=1.00233；W2 M/N=1.22710、M/R=0.99529。区间与分条件结果见主报告。小效应与不确定结果均保留。
- 保存的144组完整N/R/M输出三元组逐位一致；精简导出按预登记每输入/序列最早run保留24组三元组。
- 位级资格、exactly-once、新版sanitizer共6次0errors、正式源码/二进制/冻结表审计均通过。48项CPU测试及协议校验通过。
- 导出目录独立复算主比较、机制区间、计数和成本与原工作区完全一致；从导出源码成功重建全部三个正式程序，未增加GPU实验。
- E5 NOT_TRIGGERED；Truck未进入开发/测试。源数据、失败日志保留。
- 主要限制：E3使用新进程配对批次；有限E4无计时尾Native锚；W2是真实输入独立算子；首次规划/setup未计时；早期renderer host快照不完整。
- 串行worker保留1910.479秒，资源租赁费0 CNY（用户声明），电费未计量。GPU已释放。

入口：reports/DUAL_TOPOLOGY_PAPER_REPORT_t10.md、reports/platform_summary.json、reports/combined_review.json、REPRODUCE.md。
自动接续t10-12已关闭（PAUSED）；不得再自动重跑已完成矩阵。
最终压缩包已通过ZIP CRC、9,849文件哈希与解包CPU复算。桌面交付：/home/ubuntu/桌面/GPU双卡拓扑实验_交付_20261014/T10_实测结果_20261014。
