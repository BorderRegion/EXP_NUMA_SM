# 03 计量、运行状态与结论

## 1. 请求级数据，而不是海量审计

每个新episode预分配日志空间，执行期间不追加vector、不写JSON、不查询温度、不读回tensor。所有测量请求与窗口warmup都保存：

```
episode_id, process_block, case_id, fixture, history_profile, timer_mode,
phase(warmup/measure), window, label, global_request_index, input_slot,
request_begin_ns, context_ready_ns, launch_return_ns, ready_ns,
event_read_end_ns, cpu_ready_us, gpu_span_us, action, graph_id
```

持续时间用`steady_clock`/单调时钟的整数nanoseconds。进程开始保存一次monotonic与UTC锚用于文件/遥测对齐；不得用system_clock跨调用差直接作高精度性能。GPU事件同context、已完成再读，错误码不能被忽略。[O1]

`gpu_span_us`是事件跨度，可能包含调度/其他stream影响，不叫纯kernel busy。CPU-ready不包含随后event读取时，还要另报`event_read_end-request_begin`及trace循环间隙，不能丢掉这部分成本。[O1,O2]

condition的slot直方图必须正确：BURST_SLOT0只含0；BURST_RING4/READY_RING4按累计请求索引轮换，有限末包最多相差1。记录每个64包的提交/完成顺序，禁止复用未完成event产生虚假逐次GPU时间。

诊断header绝不修改GPU数学代码。来源`evidence/`只读。若确切错误迫使改数学kernel，隔离scope并回报，不能把它混进本轮仅计量对照。

## 2. 性能期间的运行状态

默认所有主试验继续100W动态频率，与既有证据对应；不要把“现在授权”写成“已锁频”。实际有管理入口且支持恢复时，可在一项明确原因诊断中固定保守时钟并做小型前后对照，需将状态作为独立层，不能在矩阵一半时静默换频。

本轮优先解决权限落实而不是反复提醒：仅查询已有授权入口是否可用；无入口就生成一次具体`ADMIN_COMMANDS_NEEDED.md`（由设备查询生成命令，不猜时钟值、不给宽泛NOPASSWD），其余过程继续。不得发送/保存口令或改sudo策略。

保持已有风扇/热/低RPM保护。目标设置在官方范围，保存实际readback、保护动作和恢复结果；用户授权不包含关闭保护或驱动更改。[O3]

主试验用已有1Hz遥测，记录每字段查询前后monotonic时间（字段不是原子同步）。只在少量诊断中使用同进程外轻量5Hz NVML采样，并保留observe_on/off配对（若预算允许）。5Hz轮询不等于传感器5Hz更新，也不能给每个微秒kernel配造时钟值。不得每条请求启动nvidia-smi子进程。

CPU只有有限核：主采集时关闭自己的并行编译/重型分析；不杀系统/桌面进程。日志flush、模型fit、数值参考置于episode外。记录可取得的run queue、当前CPU/线程、context switch，不能从一个指标宣布宿主干扰就是原因。

## 3. CUPTI与正式测量分开

已有Kineto/CUPTI或Nsight Systems可用即用，不安装。最多6个短捕获；捕获尽量从conditioning末尾延续到AA转折，结束后才导出。记录实际捕获范围和缺失。

只用正式无profile结果报效果，用独立profile解释时序。工具可能不导出driver API或部分Graph correlation；未知即未知。不能用“有两个stream”证明并发，也不能把串行阶段计时之和当请求总时长。[O4]

## 4. 统计（仅诊断，不训练）

AA按episode保留4窗原值；对每四窗计算：
- 有符号B/A：由实际标签定义；
- 中间/外侧：`sqrt(t1*t2/(t0*t3))`，不因BAAB而翻转其定义；
- window内前/后半、slot分层、切换后真实时间段的趋势。

CPU/GPU各自做，不混单位。每个完整四窗样本只是块内观测，独立单位是新进程块；3块的因子诊断只作探索，D4的4块也不是跨设备泛化。

LIB/SINGLE与FFN采用各块log耗时比、绝对us、配对顺序和全部原值。6块可用整块bootstrap，区间标探索性。不得将几千请求作为几千独立实验。若端点偏移、保护状态改变，要分别保留记录；不按速度筛样本。

对AA，不以平均有符号log接近0宣布稳定。预定描述线是1%与5%，同时给绝对偏差q50/q90/max、头/中/尾和raw；这些线不是选择最好协议的调参目标。不能因为只有3/4块就宣称1%等效。

对trace按实际总完成时间和每签名总贡献，不用等权shape geomean代替真实请求时间。GPU span之和单列；first/last阶段诊断不强制与正式全链闭合。

## 5. 结论卡必须分四级

1. **观察**：哪个请求/窗口变慢、在哪些条件重复。
2. **对照支持**：改变提交节奏/槽位/夹具/计时节点后，同计算有何变化。
3. **根因定位**：有明确API/计时错误，或可重复的机制干预与活动证据，才使用“导致”。仅时钟相关不够。
4. **原研究含义**：可靠性能标签是否恢复；SINGLE是否确实错选；这仍不识别物理NUMA。

可接受最后仍有未定原因，但必须指明缺哪段证据，不能只写NO_GO；同样不能强行补一个“肯定是频率”解释。不要再次自动给选择器换名字继续跑。

## 6. 精简交付

新目录一个`runs/<run_id>/`：manifest、环境/源码/构建、raw、derived、report。包含本轮全部逐请求/warmup数据、少量实际输出校验、必要trace和CPU复算入口。旧全量数据只引用路径/hash，不复制数GB。

`T10_TRANSIENT_AND_F4_DIAG_REPORT.md`前两页直接回答：AA转折是否复现/定位、修复是否独立成立、SINGLE三签名与F4分别为什么慢、哪些结论不能做。没有新增NUMA模型或重排方案，不能把测量改善包装为新GPU方法。
