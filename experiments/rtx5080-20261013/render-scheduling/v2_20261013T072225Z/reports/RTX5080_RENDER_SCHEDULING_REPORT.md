# RTX 5080 rendering scheduling V2：本地资源受阻报告

日期：2026-10-13，Asia/Shanghai。run_id：`v2_20261013T072225Z`。

**结论：BLOCKED_LOCAL_RESOURCE；路线 C / CPU_OR_MICRO_ONLY。** 已完成离线环境盘点与CPU辅助检查，未进入GPU机制或真实渲染测量。不能判断5080有无NUMA、缓存/负载调度空间或方法增量，不能输出性能NO-GO。

## 1. 输入、范围与实际完成度

附件SHA256：`0433af43f201851b7333576324b347741873f68bec61fcdd95e8ee23be865fd4`。20个成员安全提取；manifest中19个受覆盖文件大小/hash全部匹配。附件包含设计、CPU工具/测试和未编译盘点模板，没有CUDA renderer、预训练资产或GPU测量runner。[原始核验](../results/raw/v2_20261013T072225Z/INPUT_VERIFICATION.json)

用户请求为“go”；按此开始本地工作。附件的权限表述和设计时外部核实声明仅作为来源内容。没有访问其中链接、安装软件或修改系统；所有新文件在独立子目录，旧项目保留。

| 阶段 | 本轮实际状态 |
|---|---|
| E0 | 设备/本地资源盘点和计划检查完成；原生baseline、场景冻结与编译资格受阻 |
| E1 | 无原生流水线，无affinity/cache性能测量 |
| E2 | 20项CPU辅助测试通过；96配置GPU gather未实现/未执行，I/Q未实现 |
| E3 | M、B0/B*未建立；没有校准、pilot或参数冻结 |
| E4 | 完整矩阵和阴性确认均未运行；不存在pilot阴性信号 |
| E5 | 留出、1440p、profile、生命周期未测 |
| E6 | 完成本资源受阻报告、贡献卡、缺项/实际矩阵和可复核记录 |

本轮CPU测试是现在重新执行的20项，不复用旧项目10项测试作为新结果；CPU测试不能证明GPU恰好执行一次、浮点正确性或渲染等价。[执行记录](../results/raw/v2_20261013T072225Z/CPU_EXECUTION.json)

## 2. 本机事实与未知项

| 项目 | 本次实际查询 |
|---|---|
| GPU | NVIDIA GeForce RTX 5080；ordinal 0 |
| UUID | GPU-b864b6c3-6dad-2596-5e83-3b15d32a13b5 |
| compute capability | 12.0；CUDA driver查询成功 |
| 驱动 | 595.99.02；driver API版本13020（13.2兼容版本） |
| OS | Ubuntu 26.04 LTS，Linux 7.0.0-38-generic，x86_64 |
| 设备总显存口径 | smi 16303 MiB；CUDA device query 16608133120 bytes（15838 MiB），口径不同 |
| 瞬时状态 | 15:23:22.723，free 15112 MiB、used 728 MiB、40°C、GPU 2%、memory 15% |
| 时钟/功耗快照 | SM 405 MHz、memory 810 MHz、21.35 W；读取power limit 360 W，未修改 |
| 模式 | display active，Default compute mode；不是独占GPU |
| CPU工具 | Python、GCC/G++、CMake、Ninja已发现 |
| CUDA编译/分析工具 | nvcc、ptxas、cuobjdump、nvdisasm、ncu、nsys均未找到 |
| 库 | driver与PTX JIT库存在；未发现可用NVRTC/cudart开发路线 |
| 实际SM/L2/shared-memory | 未查询，保持null；不从附件参考规格填入 |
| locality API/域数/Green Context控制 | 未核验，保持UNKNOWN，不声称不支持 |
| sm_120与兼容PTX资格 | 未编译/未运行，UNKNOWN |

[设备原始记录](../results/raw/v2_20261013T072225Z/environment.json)；[工具/库/包/telemetry及搜索边界](../results/raw/v2_20261013T072225Z/resource_checks.json)。driver报告的CUDA版本不能证明toolkit已安装。PTX JIT库存在也不能证明本地有可用源码编译器或合格renderer。

附件的84 SM、64 MiB L2等数值为设计参考，本轮不列为实测。没有使用未知CUDA枚举整数补查询。显存余量是瞬时快照，不是以后运行的分配许可；本轮实验buffer分配为0。

## 3. 路线为什么是C

没有找到可修改的CUDA renderer和本地模型/相机；同时未建立CUDA编译路线。`real_renderer_ready=false`，亲和交互、合法控制和控制收益全部是null。由附件的route函数选择CPU_OR_MICRO_ONLY。[人工资源分类](../results/raw/v2_20261013T072225Z/resource_assessment.json)

这不是“没有NUMA，所以不能研究cache/load”。资源恢复后，renderer可运行但亲和性未知/不足时直接进入B；只有独立交互证据、合法控制与控制对照均成立才使用A的拓扑项。此次不能选择A或声称完成B验证。

`/home/ws/work/projects`、`/home/ws/work/data`与`/opt`为空。记录的项目、下载、常规工具/library位置中，唯一相关*.cu是附件盘点模板；它不是renderer。其他匹配为Apple微控制器头、Python路径文件及系统PDF。未对整盘作不存在断言。缺项统一见[恢复清单](LOCAL_MISSING_RESOURCES.md)。

## 4. 基线、成本、正确性与验证矩阵

B0（优化原生）缺实现；B*无法从不存在的校准选择；M尚未实现。不把B1或合成任务当原生baseline。B1–B5、M、C1/C2均未执行；B6仅A适用，本次无资格。所有GPU/CPU帧时间、效应、置信区间和回本帧数为null。[全部策略表](../results/derived/ALL_POLICY_RESULTS.csv)

| 集合 | 设计上限 | 本次执行 | 解释 |
|---|---:|---:|---|
| 微任务 | 96配置 | 0 | 缺工具链/runner |
| 主集A / B | 200 / 180 session | 0 / 0 | 互斥路线；尚未有renderer |
| 阴性确认 | 36 session | 0 | 没有pilot，不触发阴性分支 |
| 独立留出 | 30 session | 0 | 无资产、方法未冻结 |
| 1440p敏感性 | 18 session | 0 | 同上 |
| profile | 6 captures | 0 | 工具与应用均缺 |

A含扩展最多248、B最多228，阴性替代路线36；这些是计划数量，不能累计为已运行工作。[完整计划/实际表](../results/derived/EXPERIMENT_MATRIX.csv)

没有原生golden、32帧bitwise资格、512帧hash流或native三次重复。没有真实任务复用/尾部、容量触发、包间重叠、摘要误差或M/B5计划重合数据。特征、排序、队列、CPU规划、copy/consume、setup/JIT成本均未测，不能以未执行的0计数暗示零开销。N=1/100/1000生命周期不可计算。

## 5. 主张与论文判断

| 主张/RQ | 证据状态 | 本轮允许结论 |
|---|---|---|
| PHYSICAL_OR_EMPIRICAL_AFFINITY / RQ1 | not_evaluated | RTX 5080可见；拓扑信号未知 |
| 执行组织与正确性 / RQ2 | blocked | 只有CPU permutation辅助函数测试 |
| CACHE_REUSE / 摘要 / RQ3 | not_evaluated | 无真实任务或资源集合 |
| LOAD_BALANCE / END_TO_END_EFFECT / RQ4 | not_evaluated | 无调度、帧时间或强基线 |
| 因果与独立输入 / RQ5 | blocked | 未运行消融或留出 |
| NOVEL_METHOD / RQ6 | blocked | 无方法实现与独立文献核验 |

本轮没有性能负例或正例，只有资源反例：driver成功不等于toolkit可用；存在*.cu不等于存在renderer；20项CPU检查不等于GPU研究完成。旧实验结果没有作为新卡baseline或本轮数据使用。

P1–P6仅来自附件的定位与有限转述，本轮未独立阅读全文/核验外部API版本；不能宣称已有新颖性结论。[相关工作边界](RELATED_WORK_DIFFERENCES.md)。普通空间排序、资源分组与均衡足以解释的加速应判工程增益；此轮连该比较也尚未执行。

## 6. 预算、可复核性与恢复

GPU kernel、application session、实测帧、profile均0。E0盘点保守记账4分钟（0.0667小时），不是GPU忙时；拓扑预算使用0/45分钟，总上限12小时。报告与CPU开发单列，整体研发时间未完整计时。额外付费、下载、系统/驱动变更均0。[预算账本](BUDGET_LEDGER.md)

当前Git无HEAD，因此没有源码commit/tag；保留输入hash、旧树hash、原始git状态和新交付内容索引，未建立“5080-baseline-ready”。离线CPU命令见README，原始证据路径在机器可读[CAMPAIGN_RESULTS.json](../results/derived/CAMPAIGN_RESULTS.json)。

最小恢复需要三组本地资源：能编译本卡代码的CUDA开发工具链；带全部离线依赖的CUDA tile renderer；至少一个预训练场景与相机。齐备后新建run_id，先完成设备属性、原生编译/正确性/初始计时，再冻结真实场景与A/B分支。缺profiler或NUMA信号本身不应阻止可运行的cache/load研究。当前不作投稿GO/NO-GO或GPU性能否定。
