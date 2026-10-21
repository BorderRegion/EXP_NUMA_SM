# 实验矩阵、计量与统计合同

所有数字是预注册上限或设计值，不是已运行结果。所有日期用实际运行UTC和本地offset；不要回填成设计日期。

## 1. 主矩阵与分支

| 集合 | 构成 | 最大session/配置数 | 作用 |
|---|---|---:|---|
| 微任务 | 4工作集×3复用等级×2倾斜×4固定调度 | 96配置 | 机制与索引正确性；不是96独立应用 |
| 完整主集A | 2场景×2测试轨迹×10策略×5进程块 | 200session | 拓扑＋缓存路线 |
| 完整主集B | 2场景×2测试轨迹×9策略×5进程块 | 180session | 无拓扑项路线 |
| 留出 | 1独立场景×2轨迹×3冻结策略×5块 | 30session | 不参与校准 |
| 分辨率敏感性 | 2开发场景×1预定fast轨迹×1440p×3策略×3块 | 18session | 不是重新调参机会 |
| 阴性确认（替代完整主集） | 2场景×2轨迹×3策略×3块 | 36session | 没明显pilot信号也有独立确认 |

因此完整A最多248、B最多228个应用session；阴性路线36，不追加留出/1440p找赢家。场景不足按实际分母报告，不复制同一资产凑数。

主分辨率1080p；显存或单kernel安全不允许时，在方法计时前固定降低的共同分辨率并报告，不边看收益边选。4K不在首轮。

每session预热至少256帧且至少2秒，测512帧。预热必须执行该策略完整特征/构造/消费路径，不用无效占位metadata让候选在计时才首次执行。

## 2. 校准、pilot与留出

每开发场景一个校准轨迹，只用于参数与B*选择。方法每项最多12组配置，两次独立校准重复；共同executor参数在更早identity/SFC资格后冻结。用户已有自然路径可用，没有就以场景包公开相机插值生成固定非实时输入，并记录构造规则。

在方法确定前，把测试slow/fast和留出场景的选择原则、frame IDs、负载顺序、seed写入锁文件。测试阶段不选择参数、签名、cache阈值或新算法。查看结果后的修改需新campaign，不继续复用同一留出作独立证据。

可选pilot最多2校准场景×1校准片段×3策略（B0/固定强simple/M）×2块×128 measured，预算算E3，不用于正式区间。pilot只选择完整或阴性确认分支，不把小样本赢家当结论。

## 3. 计时边界

每frame至少：

- CPU从输入准备/submit到实际结果可用的墙时；
- 完整GPU渲染帧事件区间；
- 原preprocess、原sort/binning、feature、taskbuild、render、copy/consume分段；
- 额外显存与allocator驻留；
- 输入与输出的合同状态。

分段之和不是有重叠执行时的critical path。GPU event不能覆盖CPU规划，因此若规划在CPU主指标必须包含CPU。

setup、模型加载、PTX JIT、mapping、静态表构建、snapshot及大文件落盘分开。不可把在线每帧重排归到setup，不可用未来帧数据预计算计划。

主结果是动态真实帧，所有上游每帧执行。对捕获tasktrace的重复render只报kernel机制，不称端到端。

## 4. Cache与profile

正式结果不启动重型profiler、不人为清缓存。每session使用真实warmup，让策略本身形成cache状态；不同策略phase重置逻辑状态，缓存不宣称完全相同。

微测试可有显式cache-priming/working-set准备，但必须标 regime，不称操作系统无副作用“全cache冷启动”。

Nsight Compute默认可能flush cache并serialize/replay；设计时官方建议cache敏感工作使用application/range replay和明确cache-control。按本地版本能力设置，不能不检查就抄最新flag；策略间完全相同，结果与无profile计时分开。不得更改系统全局时钟或申请管理员只是为某counter。

可得时采集L2/DRAM字节、L2命中、eligible/active warps、长延迟stall、原子/队列成本、实际CTA任务数和本地循环尾部。没有指标则null+原因，不用软件proxy填硬件字段。

## 5. 拓扑/复用的可证伪对照

A路线：M的域映射与置乱映射保持数据内容、计算服务率和容量约束一致，仅改变匹配。没有真实assignment证据就不能claim拓扑收益。

B路线：资源摘要在相近工作量桶内置乱，分离缓存信息与重任务排序；cap消融保留摘要/队列成本。置乱会改变bundle大小或尾部时必须量化，不将它视为纯单因素。

空间排序、load-only、resource-only、simple group+balance都是真正强对照。M与B5输出同样计划时报告重合率，不反复调M制造形式差异。

增加固定单位的working-set sensitivity只是synthetic；不通过复制场景、保留无用缓存或填满显存让应用人工memory-bound。

## 6. 正式统计

每进程块各策略都完整运行，顺序以固定种子平衡随机化。5块是主要重复单位，512帧不是512独立实验。场景/轨迹等权；metadata bootstrap按块、在配置内分层，探索性95%区间。

主比较：M/B0、M/B*。B*只从校准选定；测试中逐配置最优只作“事后有限策略包络”，不算已部署方法。完整展示各策略的负例与成本。

每块先计算完整512帧均值，形成log(M/B)，几何汇总。分别给绝对ms、时间下降率100*(1-M/B)；吞吐提升B/M-1另列，不混用。不能把原生5080与旧4060时间相除称方法加速。

p50/p95/p99按session先算，再按块报告分布/区间。512帧的p99约由顶部少量帧决定，只作探索性；没有长时延实验不得写硬实时、游戏端到端或动态尾部保证。

若需确认尾部，必须事前指定配置与更长轨迹，来自预留预算且报告分配，不能看到p99赢家后只延长该方案。默认首轮不追加。

运行异常：输入错误/设备故障/合同失效的整配对块标invalid；raw保留，并在预算内一次完整重跑。热漂移指标仅做事前质量标记，不根据谁快删块；预算不能覆盖时报告不完整及敏感性，不伪造平衡数。

## 7. 预算口径

worker占用包括该worker被实验保留时的build/setup/JIT/等待/profile；GPU timestamp busy与CPU-only开发/分析另外计，不能重复相加。

总12小时是硬上限，阶段预算见campaign.json；未用额度不自动改变研究范围。reserve只用于注册的修复、固定profile、观察扰动对照或缺失配对，不再加新算法。

## 8. 每次运行的数据

`run.json`：campaign/experiment/run/block/phase IDs，真实时间、git commit/dirty patch、本地工具版本、设备UUID/cc/SM/L2/VRAM、CUDA配方、native/PTX模式、backend/model/camera hashes、strategy、executor、路线A/B、raw来源。

`frames.csv`：frame_id、simulation_time、GPU_frame_ms、CPU_result_ready_ms、stage times、feature/build overhead、task/bundle counts、list-length summaries、estimated_footprint（明确proxy）、queue counters（是否诊断）、allocation/map generation、memory current/peak、output hashes/finite。

`timing_scope.json`：每个时间字段起止点、包含/排除内容及是否重叠；未测量字段null。

`hardware.csv`：只读telemetry、温度/clock/power可用项、后台使用；不推断独占状态。

`topology.json`：API声明、测量证据、可利用验证、校准/验证epoch、地址范围和实际位置覆盖，分开。

`quality.json`：完整输出资格帧、逐frame筛查hash、异常raw、任务双射、多次重复、source不变量、未验证范围。hash一致不能冒充全程序形式验证。

## 9. 最终图表必须由raw重建

1. 5080实测能力与来源区别；2. affinity交互/未知范围；3. 工作集与并发曲线；4. task负载/复用分布；5. B0/B*/M完整帧配对效果；6. 全部基线；7. queue/特征等成本；8. 置乱/cap消融；9. 留出与分辨率；10. 生命周期及预算；11. 主张—证据—限制矩阵。

不画虚构示例性能图。不支持或未执行的格子写明原因。论文级评估尚缺第二独立程序/架构时统一记录，不自动跨卡采集。
