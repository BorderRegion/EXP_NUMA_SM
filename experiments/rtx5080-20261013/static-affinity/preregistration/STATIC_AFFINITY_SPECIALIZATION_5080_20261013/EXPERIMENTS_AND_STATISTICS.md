# 实验矩阵、计量与统计合同

以下均为新计划上限，不是已运行数据。不强行花满预算，不用重复同一配置填缺失格子。

## 1. 总体矩阵

| 阶段 | 上限 | 输出 |
|---|---:|---|
| E1亲和矩阵 | 5allocation × 3工作集 × 2load配方 × 2并发条件 = 60 strata；每stratum最多64区域、6轮 | 真实SM/资源组×区域覆盖、交互、稳定性与分配适用域 |
| E2控制 | 最多2种后端；每种最多3个资源/occupancy配方 | 实際位置覆盖、恰好一次、Native与matched成本 |
| E3固定机制 | 3工作集 × 3访问分布 × 6策略 × 5独立块 = 270 sessions | table/常量/匹配的效果与开销 |
| E4渲染快照 | 2场景 × 4snapshot × 8策略 × 5独立块 = 320 sessions | 同输入固定render-stage机会 |
| E5动态主矩阵 | 2场景 × 2轨迹 × 5独立块 × (8策略+1Native尾锚) = 180 sessions | 完整渲染增量、每帧开销与尾部 |
| E6留出 | 1现有Truck × 2轨迹 × 3策略 × 5块 = 30 sessions | 冻结规则的场景外推 |
| E6分辨率 | 2场景 × 1轨迹 × 3策略 × 3块 = 18 sessions | 1440p敏感性，不称全面尺度泛化 |
| E6分配/生命周期 | 3场景/分配事件合同 × 3策略 × 5新进程 = 45 sessions | 重新分配、scene切换、capacity增长的guard与重新标定成本 |
| 阴性确认替代 | 最多36 sessions，替代完整动态矩阵 | 固定范围负证据，不调新参数 |

E3的六策略固定为N/I/A/T/K/P（访问分布固定为均匀、偏斜、多资源共享；不能只测最适合map的单home任务）。不支持K时保留缺格而不换第七策略。E3每session32 warmup replay+128 measured；E4为64+256；这两者是单kernel/快照重放，不能等同于动态帧。E5/E6正常应用为至少256帧且2秒的实际预热+512测量帧。阴性确认256测量帧。全部时长受24h worker总账约束。

E1的60 strata按workset/load/concurrency划分；缓存准备、窗口粒度属于层内的预注册子条件，不将其隐形计为一次观测。初始有限侦察后冻结主条件，完整数目写actual matrix并受E1时限约束。

E4设计顺序：先用校准子集决定是否进入主application；快照table可按快照特化的结果叫`SNAPSHOT_SPECIALIZED`。场景静态计划由开发相机建立再测未参与校准快照/轨迹，必须另列，不给测试每帧免费未来信息。

## 2. 分层冻结与留出

- 硬件测量配方在E1前3allocation后冻结，后2allocation不调算法。
- 同地址跨轮稳定性不等于地址重分配稳定性。
- 场景计划最多16开发相机，不使用fast/slow测试轨迹时长或成本选分配。
- Train/Bonsai作开发场景；已有Truck只作独立留出，不作为看到负结果后的额外调参资产。
- 旧fast/slow是相机索引步幅，不标定物理速度，继续准确命名为`stride_fast/stride_slow`。
- 测试地图的allocation初始化标定允许执行，但方法已冻结且成本全部进入生命周期，不允许从正式测试帧产出plan。

## 3. 主测量量

### A. 亲和性
每load样本保留原elapsed cycles/单位、smid开始结束、区域、依赖链次数、load recipe、缓存准备、并发、seed、allocation generation。局部cycles仅描述本线程区间，不能直接当全GPU可节省时间。

报告`coverage_sm_region`、每格count、region组偏好、独立test匹配效果及未知项；只在实际可控制组里计算部署可行映射，不从最好的任意SM列作不现实oracle。

### B. 完整执行成本
每帧：CPU输入至GPU输出就绪、完整GPU流水线、preprocess、binning/sort、render、mapping setup、额外copy/sync/event、table/launch管理。若event区间包含CPU空档，明确标签，不能称GPU busy。

所有队列/roster/prepare都不允许在计时外重置后假装免费。相机输入和原算法正常sort允许；新增调度禁止重新逐帧做。输入与结果读回日志在所有策略中对齐。

### C. 开销分离
1. Native→matched blind：执行控制本身成本。
2. matched blind→correct map：映射有用性。
3. correct map→balanced shuffled map：位置—数据关系贡献。
4. table→constexpr same plan：编译固化的额外价值。
5. layout-only/assignment-only/full：数据布局和任务分配交互，最多预定12个附加诊断格，使用预留，不加入新布局。

### D. 负载
每组逻辑任务数、candidate数/估计工作量、实际完成区间、空组fallback比例，首尾tile执行位置抽样；没有硬件计数不作native occupancy/remote traffic数字。

## 4. 正确性数据

固定uint机制由独立CPU算法给出精确输出。小域枚举task所有权、缺组映射与重复SM的情况。

渲染资格：同帧Native三次重复；参考frame池每场景至少16个固定输入，包含空tile、重tile、边缘viewport(321×181)和1080p。比较完整color/final_T/n_contrib；改变布局时逆映射后比较。native自身不重复则冻结该条件，不能拿一份golden放宽。

每个正式session最终完整输出对照；预先选中的首/中/末帧完整保留；逐帧finite和两个64bit digest是screening，不是形式等价。digest写入额外scratch不污染下一帧；保持所有策略相同，按预定少量无逐帧digest重复评估观察扰动。

无意外UB、命中次数改变或逻辑任务丢失。未知localmemory/SM迁移只降低机制结论，不自动放宽输出标准。没有ComputeSanitizer时记录缺项，不能因此称已sanitizer-clean。

## 5. 随机化、配对与独立单位

进程块内共享相同逻辑输入、scene和allocation生命周期。Native开头与结尾锚；中间7策略用固定seed随机顺序，跨块轮换。每phase独立运行同样热身，不能候选紧接基线而省热身。

E5每条件5个独立process block。先算每块candidate/reference均值比与绝对差，再按scene/track等权汇总log比。bootstrap按process block在stratum内重采样，20,000次并记录seed。512帧不算512独立重复。

主对比冻结为K(不可用则T)对N和B*；其他多比较为探索性。若作确认性多项比较预注册Holm或报告同时区间，不事后选择显著的一对。

topology samples使用allocation/round层级CI；错误地汇总数百万loads会产生过窄区间。细热图是描述，不是每格都独立显著。

NoSER/SER与本题无关，不加入旧结果。不得跨4060/5080比较成方法加速。

## 6. 开销“接近零”的诚实口径

逐帧planner调用数、schedule D2H字节、计划H2D字节、计划重新生成数，在代码路径和实际日志中均应为0。初始化/容量事件明确另表。

额外启动次数、只读table字节、地址运算、cooperative grid barrier数量可能非零。报告各自数据，不能把它们统一写为0。

用matched identity micro估计残余成本和区间；区间覆盖0时只能称未分辨，报告上界，不称数学零。正收益也不证明零开销。

## 7. 无收益/未知不能混写

- 缺coverage→`AFFINITY_UNRESOLVED`，不是无NUMA。
- 有map但无法控制→`CONTROL_UNAVAILABLE`。
- 有control但不快→`AFFINITY_SIGNAL_NO_NET_CONTROL_GAIN`。
- 快照快、动态慢→`SNAPSHOT_GAIN_DYNAMIC_NOT_ESTABLISHED`。
- 全部快但可由已有简单方法解释→`AFFINITY_ENGINEERING_GAIN_ONLY`。
- 新规则有独立增量、完整成本后快且适用域清楚→`STATIC_AFFINITY_PAPER_OPPORTUNITY`，仍非录用保证。

没有信号时只作两次预定独立确认，不搜第三种控制算法或改成cache-only。

## 8. 数据文件与字段

`environment.json`：实际版本、cc/SM/L2、支持API、local库/模型位置、健康限制；不写隐私口令。

`allocations.jsonl`：allocation_id/generation、大小、逻辑内容hash、实际分配方式、地址映射证据、初始化者、有效期、失效原因。

`affinity_samples.jsonl`：epoch/round/seed、observed_smid_begin/end、resource_group、region、虚拟offset、粒度、working_set、priming、recipe、clock_ticks、iterations、checksum、status。

`control_runs.jsonl`：kernel/layout/plan hashes、actual roster或组、每组task数、missed/duplicate task数、migration观测、control开销、完整输出。

`plan_manifest.json`：可依赖的信息/禁止的信息、calibration refs、task/region映射、template配置、generation guard、fallback、source/compiled hashes、必要init成本。

`frame_metrics.csv`：run/block/policy/frame、输入hash、init_generation、CPU_ready_ms、GPU_pipeline_ms、preprocess_ms、sort_ms、render_ms、launch_setup_ms、planner_calls、schedule_D2H/H2D、taskcount、fallback、memory和正确性screen。

`init_costs.jsonl`：C_research/C_device/C_allocation/C_scene/C_compile，各有实测/估计标志；base共同成本与候选额外成本分开。

`claim_evidence.csv`：每个主张、来源、证据类型、实验ID、支持范围、未测项。

## 9. 论文图表

1. 位置×区域原始热图、去主效应残差和覆盖mask，三者分开。
2. 亲和地图同allocation/新allocation确认；有采样缺口直接显示。
3. 实际task placement与预测组的混淆/覆盖图，不能只展示计划。
4. N/I/A/T/K/P机制对照与初始化table/编译常量开销。
5. 固定快照与完整动态pipeline分开的配对效果。
6. upstream+render+新增成本分解；绝对ms与比例都给。
7. 负载分布、空组fallback、映射失效和额外内存。
8. N=1/100/1000/10000生命周期曲线与回本区间。
9. 留出/分辨率/新allocation未执行矩阵。
10. 贡献对照表：S1静态NUMA、普通空间/负载方案、本候选真正差异。

工具可用则用已有绘图栈，不能为出图触发在线安装。没有数据就给空表和理由，不绘制虚构示例收益。
