# GPU 访存亲和性与不规则渲染机会报告

**最终状态：BLOCKED_LOCAL_RESOURCE。** 本轮完成E0盘点、预注册、CPU分析准备和资源受阻分支的E6交付。
主机为**RTX 5080、16GB、计算能力12.0、Ubuntu26.04、驱动595.99.02**。
缺本地CUDA编译器/官方开发头、小测量runner、renderer/预训练资产和离线文献，
因此**实际GPU kernel测量0次、渲染session 0个**，尚不能评价亲和性或渲染收益。
不能把资源阻塞判为NO_ACTIONABLE_AFFINITY_ON_THIS_GPU，也没有依据要求换卡或租卡。

日期：2026-10-13（Asia/Shanghai）。run_id：affinity_20261013T064931Z_b2cdc88d。
需求来源：preregistration/CODEX_MASTER_TASK_v1.0.md；其SHA-256见campaign.json。

## 任务书要求的12项直接回答

| 问题 | 本轮答案 |
|---|---|
| 1. 本机公开域API与实际SM/地址？ | CUDA主机初始化成功；locality/Green Context域API因官方headers缺失全部NOT_QUERIED。实际SM ID和设备缓冲区地址均NOT_MEASURED，未申请探测缓冲区。 |
| 2. 是NUMA、经验亲和、竞争还是不足？ | 证据不足；未取得任何访存矩阵，不对结构或竞争作归因。 |
| 3. 交互模型在留出是否胜过SM+地址偏差？ | 硬件上UNKNOWN。CPU分析器在明确SYNTHETIC数据上通过有/无交互及失效地图检查；不构成硬件证据。 |
| 4. 能否合法改变任务—数据匹配？ | 尚未验证。无kernel、实际assignment、SM组或队列；只读GPU访问成功不证明亲和执行控制。 |
| 5. 对B0、queue、排序、均衡、静态NUMA各快慢多少？ | 全部NOT_MEASURED；没有0%或估算收益占位。 |
| 6. 特征/标定/分组/额外访存和存储成本？ | 应用成本UNKNOWN；本轮GPU申请显存0、标定0次。CPU工具运行时间单列预算，不作为renderer成本。 |
| 7. 置乱是否消除增量？ | 硬件上NOT_MEASURED。CPU固定置乱仅检查分析方法；E2/E5同执行器拓扑消融尚未运行。 |
| 8. 渲染算法与输出合同是否保持？ | 未接入renderer，资格NOT_ESTABLISHED；未做像素、透射率、n_contrib或post-hit随机维度检查。合同已冻结，不能宣称正确性通过。 |
| 9. 后端间不能外推什么？ | CUDA smid/普通缓冲区不证明Vulkan图像或opaque RT资源位置；SER提示不等于SM绑定。CPU检查不能外推GPU，CUDA 3DGS也不能改称RT Core渲染。 |
| 10. 相比列举工作真正新增什么？ | 当前新增是实验准备和可验证CPU分析工具。无已证实新方法；原文献/官方资料缺失，新颖性UNVERIFIED。 |
| 11. 下一步是换GPU、更多程序还是停止？ | 先恢复当前主机离线toolkit、runner与文献，完成预算内短E1；只有稳定交互与控制可行才进E2。当前不能判断需换GPU。 |
| 12. 支持的最强主张？ | 支持环境/资源事实和分析软件自检；研究主张A–E目前均无硬件或应用实测支持。 |

## 实际环境与资源门

主机只读CUDA调用：cuInit=CUDA_SUCCESS；cuDeviceGetCount=1；
cuDeviceComputeCapability=12.0；cuDeviceTotalMem_v2=16608133120 bytes（15838MiB）。
nvidia-smi设备级快照：总16303MiB、空闲15026MiB、已用814MiB、40°C，display active。
CUDA driver兼容版本13.2不代表toolkit已安装；nvcc/ptxas、NVIDIA cuda.h、ncu/nsys未找到。
SM数、L2容量、域数、cluster能力保持UNKNOWN，没有硬编码属性枚举或套用别的架构。

沙箱内cuInit为CUDA_ERROR_NO_DEVICE；经批准在同主机沙箱外只读盘点成功，
所以不是“主机没有GPU”或已证实驱动损坏。GPU正在承担桌面显示，为非独占；
本轮不终止其他进程、不启动旧campaign、不改系统、不联网、不付费。
搜索范围和原始成功/失败返回值见环境报告和两份environment JSON。

本项目初始没有实验文件，常规本地项目/数据/工具目录无renderer、模型或场景候选。
任务书引用的SOURCES_AND_SCOPE.md未随附；不能离线确认引用内容和新颖性。
未检查到可构建renderer，因此没有触发其潜在下载步骤，更没有为补依赖联网。
全部缺项集中于reports/LOCAL_MISSING_RESOURCES.md，不扩大探测或开发任务。

## E0–E6进展与门

| 阶段 | 结果 | 后续门 |
|---|---|---|
| E0 | 完成实际主机/资源盘点、差异卡、预注册、种子/阈值/预算和输入合同 | 工具链与测量runner不足 |
| E1 | BLOCKED_LOCAL_RESOURCE，未编译/启动GPU程序 | 无实际SM×地址矩阵，不能给科学阴性分支 |
| E2 | NOT_ENTERED | 缺E1稳定交互、独立复验和合法控制证据 |
| E3 | 资源预检查完成，无真实候选；APPLICATION_RESOURCES_MISSING | 无资产和CUDA入口，不新写renderer |
| E4 | 候选和B0–B5/M/C合同已冻结；方法未实现 | 不因缺测量先开发论文级系统 |
| E5 | 160session顺序表已准备，真实场景/轨迹slot未绑定；运行0 | 无资格和信号，不能执行或解释占位顺序表 |
| E6 | 本轮资源受阻分支报告、raw/derived、预算、贡献/差异卡、准备包和导师短稿完成 | 后续需实际资源恢复，另存新run |

## CPU准备的验证与限制

tools/analyze.py只用标准库，按GPU/driver/process/context/allocation/cache/load/workset/epoch分图。
访存链先按dispatch再按split取单元中位数，保留稀疏SM ID、缺单元和迁移样本；
校验checksum与自有地址边界，比较additive模型与经验交互的同分配留出预测。
完整矩阵上置乱交互SM标签，保留SM/地址主效应，不强制两域，不命名物理GPC。
**工具不完成未见地址推广、三进程/新分配复验或合法执行控制，不能自动授权E2。**

session统计在校准集选最强B1–B5，全部measurement帧算术平均，
按process block形成配对log比值，场景/轨迹等权、块bootstrap，报告全部对照。
整理中发现首版session用了中位数，已改为任务要求的平均口径；旧source/raw保存，
新版本加入均值9ms而中位数1ms的偏斜帧断言。硬件未测，未因性能结果更改阈值。
生命周期只计算实测范围，负/零净节省无break-even，512帧不外推1000帧。

最新版10项科学逻辑检查全部通过，两个CLI入口均通过实际读写验证。
CPU原始fixtures和派生结果全部保留，不选赢家、不伪称硬件/渲染观测：

| 合成数据 | 同分配screen | 解释 |
|---|---|---|
| additive SM偏差+地址双峰 | 未触发 | 无交互不会因双峰自动叫NUMA |
| 人为注入交互，独立留出噪声 | 触发描述性candidate | 分析器有检测能力；不是RTX5080信号 |
| 留出反转地图 | 未触发 | 失效地图被验证拒绝 |

其他检查：缺单元不补、迁移单列、checksum/越界/run泄漏拒收、session缺配对拒收，
校准最优与测试最优不同仍保持冻结选择；应用完整输出资格仍未建立。
GPU三新进程/新分配/新地址和5进程应用数据都没有，CPU重复不能代替它们。

## 本轮硬件/应用结果和完整成本

| 比较 | 目标pass节省 | 完整frame节省 | 拓扑机制 |
|---|---|---|---|
| M vs B0 原生优化renderer | NOT_MEASURED | NOT_MEASURED | UNKNOWN |
| M vs B1 同queue拓扑盲 | NOT_MEASURED | NOT_MEASURED | UNKNOWN |
| M vs B2 调优普通局部性 | NOT_MEASURED | NOT_MEASURED | UNKNOWN |
| M vs B3 仅负载均衡 | NOT_MEASURED | NOT_MEASURED | UNKNOWN |
| M vs B4 静态亲和/正常公开API策略 | NOT_MEASURED | NOT_MEASURED | UNKNOWN |
| M vs B5 共享分组+均衡 | NOT_MEASURED | NOT_MEASURED | UNKNOWN |
| M vs C 固定置乱拓扑 | NOT_MEASURED | NOT_MEASURED | UNKNOWN |

没有模型/地图、actual assignment、queue时间、资源复用、DRAM/L2计数、extra VRAM或render输出。
这些字段都是未测，不是零开销。生命周期N=1/100/1000和回本帧数均不可计算。
实际GPU探测buffer/worker/kernel/session均为0；总GPU预算12h没有消耗。
CPU工具runtime与会话工作墙时见reports/BUDGET_LEDGER.md，后者含编程/审批等待，
不伪称GPU实验worker或CPU纯计算时间。

## 贡献判断与接续建议

当前无TOPOLOGY_APPLICATION_OPPORTUNITY、MICRO_ONLY或GENERIC_LOCALITY结果可报告。
“亲和+共享+负载”不能仅凭任务书标题宣称新颖，OO-VR等比较仍需离线原文核验。
唯一候选仍为有限greedy联合成本；没有证据允许扩展ML、动态复制或通用runtime。
恢复后先查本地公开接口和L2/SM，构建有界E1runner，完成跨进程/分配与新地址验证；
E1阴性就收尾，有信号但控制缺失按对应分支收尾，E2没有净增量不改renderer。
资源表和artifacts/MINIMUM_VALIDATION_PACKAGE.md列出唯一准备清单，不自动租卡或接远程平台。

## 交付索引与raw选样规则

- reports/ENVIRONMENT_AND_CAPABILITY.md：环境、能力、查询失败/成功与搜索边界。
- reports/LOCAL_MISSING_RESOURCES.md：集中缺项和最小恢复条件。
- preregistration/PROTOCOL.md、RAW_SCHEMA.md、SESSION_ORDER.json：冻结合同和待绑定顺序表。
- reports/CONTRIBUTION_CARD.md、RELATED_WORK_DIFFERENCES.md：机会与未核验差异。
- reports/COUNTEREXAMPLES_AND_NEGATIVES.md：环境反例、CPU阴性与失效地图证据。
- results/raw/affinity_20261013T064931Z_b2cdc88d：两份环境raw、首版和更新版完整SYNTHETIC fixtures。
- results/derived/同run_id：完整CPU分析、自检和CLI验证结果；无hardware结果。
- reports/BUDGET_LEDGER.md、SUPERVISOR_BRIEF.md：预算和导师短稿。
- tools/：3份标准库程序和使用说明；没有现成GPU harness或renderer。
- artifacts/：旧版源码、唯一验证准备清单和完整交付归档。
- manifest.json：源代码、结果、文档hash、执行状态/driver/参数和成本口径。

选样规则：保留全部两份环境盘点、三个CPU亲和fixture、全部合成session及两版分析，
没有筛选硬件阳性或删除负例；硬件raw不存在，不用合成填补。
