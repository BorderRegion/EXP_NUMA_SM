# T10：冻结 NUMA 候选规则的机制与部署验证
## 2026-10-16 / 有限连续补充实验

## 1. 这次到底做什么

**不发明新调度器。只把现有 0x33 规则在不同执行条件下检验清楚。**

要一次回答五个问题：
- Q1：不再重新挑 mask、方向和 SM 组，旧规则在新分配和新轮次上还有效吗？
- Q2：它跟随真实地址/计算位置，还是跟随任务编号、数据内容或最后的读取者？
- Q3：低并发、重复访问得到的偏好，能否迁移到一次完整的并发消费？
- Q4：把 clocks、SM 读取、diagnostic store 真正从正式 kernel 移除后，匹配方向和净效果是否改变？
- Q5：证据支持物理 NUMA、条件性经验亲和、缓存/顺序效应，还是仍无法判定？

旧结果只支持：2 MiB/细分控制条件下存在短规则；32 MiB 不稳定；原 micro 正式核仍有诊断；T/M 读取的物理地址集合相同。不能预填 NUMA 存在、不存在或 paper 成立。

## 2. 本轮冻结，禁止重新找赢家

`FROZEN_RULE.json` 从**旧 fine_shift_0 开发数据的 2 MiB 行**生成，不使用旧确认集里最快的实例：
- mask=51（0x33）；64 个虚拟 region；每条带 4 KiB。
- PAIR4SM：C0={24,25}，C1={20,21}，bias=1。
- BALANCED56SM：两个确切的 28-SM 集合见 JSON，bias=0。
- 同一组、同一方向用于 2 MiB 和 32 MiB；32 MiB 是小集合规则的迁移检查，**不重新拟合它自己的 mask**。
- runtime 句柄编号可以变；实际 SM 集合不能未经说明地变。通过现成公开资源对象和 roster 找回原集合，不把旧 fine_group ID 当作永久物理 ID。
- 无法从本次完整资源对象重建某个集合，该 scope 标 `FROZEN_RESOURCE_SET_UNAVAILABLE`，继续另一个 scope、资格和 CPU 分析；不换一个更快组补位。

**不重搜 1..63、不根据新数据翻转 bias、不取绝对值美化负交互、不重新挑最快两个组、不把失败的新分配重标定成成功。**

初始化允许重建句柄、观察实际 roster、产生逻辑输入。新分配可以复用物理页；记录 generation/VA/offset，不能宣称物理页独立。

## 3. 代码改动集中在一个共同 consumer

复用现有 CUDA 13.2/driver、Fine/Green 构造、parent-stream Graph fork/join、uint64 归约。只新增：
1. 一个共同完整 region consumer，能切 grid=2/32、visit=1/8、inner repeat=1/4。
2. 它的编译期 `DIAG=true/false` 两个实例，数据计算体一致。
3. 明确的四格与两种 joint 对照，及既有 N/T/M/P 的无诊断版本。
4. 清楚的 primer、输入变化和计时/统计记录。

**不新增生产任务表**。mask 已固定，可直接用 `__popc(region & 0x33)` 与位插入；原标量地址、bias、长度不是逐任务 LUT。任务顺序控制使用固定仿射置换的整数表达式，见内核文档。

主对照只改变完整 region 到执行组的匹配，输出按**物理 region/visit**固定写回，避免换匹配时连输出地址也换了。M 着色布局仅用于 S4 复核，单独说明其逻辑输出映射；它不是主物理证据。

不得把 Green 分区、多次计算分支叫“额外小调度 kernel”。本轮主消费者两个实质计算分支已经 Graph 化；不再新增 planner、D2H 决策或 per-task launch。缓存 primer 是显式测量干预，和部署成本分别报告。

## 4. 一次性顺序：S0—S5

### S0：运行状态、规则与最小源码资格（预算 0.5 worker h）

主功耗条件固定 100W；使用用户已经批准的支持范围内 T10 状态控制，按 `docs/POWER_AND_LOGGING.md` 协调保护服务。**本轮不再增加 125W 数据族。**
保存前状态/恢复方式。查询本机实际权限；没有管理权限时一次列清，保留已有100W条件继续可做部分，不反复询问。固定功耗不宣称固定频率。

核实旧开发源中的规则和组集合，写新 freeze；小输入检查 slot 双射、覆盖、错误边界、同数据输出，保留最小 sanitizer（现成可用时）。不复查整套旧文件或重新搭验证框架。

编译 clean consumer：SASS 不得有 clock、SM读取、diagnostic/ownership store 或 atomic。不是 `diag=nullptr` 就算完成，必须经编译期消除。注册数/共享存储差异记录，但不人为填 dummy 指令强求相同。

### S1：冻结方向的局部规律复验（0.75 h）

6 个新进程/分配，每个按旧移位 probe 的局部消费方式检查 2/32 MiB：28 fine groups、4 轮、grid=2、512 个重复 region-task、`.cg`、one-pass、旧式 same-group warmup。地址/CTA/组先后由预定 seed 改变；不得重拟合。

保留实际 CTA 原值，按冻结方向计算固定组对/合并组的 region 对比。输出每轮符号、交互及早晚相关。它是诊断、有 clocks/SM，不与后续 clean 计时混池。2 MiB 与旧正例比较的是规律方向，不直接比绝对周期；32 MiB 是独立的失败/适用域对照。

如果这里不复现，也**继续既定 S2—S4**：失效本身需要明确，不能省略真实执行或重选规则。

### S2：同一 consumer 的四格＋并发桥接（1.5 h）

两种集合、两个 frozen scope，三个执行形态：
- L8：每组2 CTA、每类32 region、8次完整 region-task visit；每 visit 都独立写结果。
- L1：每组2 CTA、同一集合仅一次 visit。
- H1：每组32 CTA、同一集合仅一次 visit。

所有主结果使用 DIAG=false。每个 cell 固定 COMMON_PRIME；它由 primary/full-resource 固定 sweep 完整输入，然后再开始 consumer 计时，不由“上一个测量策略”决定 warmup。保留 primer 成本但不要让它淹没 consumer 主结果。

每形态六动作：C0D0、C0D1、C1D0、C1D1、J_MATCH、J_REVERSE。
四个 CELL 分别测完整类在指定组上的完成时间；JOINT 两组先全部提交再 join，不能把串行 CELL 时间相加冒充 JOINT。

总上限：2尺寸×2scope×3形态×6动作×6进程 = **432 phase**。
输出有符号交互、J_REVERSE/J_MATCH 和低→高并发的交互变化。跨 L8/L1/H1 不把时间直接相减归为“延迟”，按实际工作量解释。

### S3：缓存来源与坐标反事实（1 h）

只测 2 MiB、H1、DIAG=false，不添加第三个大小。八个预定 profile：
1–4. PAIR/FULL 各做 OWNER_C0、OWNER_C1；owner必须读**整个集合**，不是只读自己类别。
5. FULL 的128MiB自有scratch干预；不称硬件cache flush。
6. FULL/COMMON_PRIME，只交换 r与r^1 的 payload 内容，地址访问集合和域类不改。
7. FULL/COMMON_PRIME，只重命名 r'=r^1，保持物理地址与任务归属不变，使用补偿后的类公式。
8. FULL/COMMON_PRIME，活跃基址平移128B到同一更大合法分配内；mask不改、不重新选方向。

第7项纯标签重命名是CPU索引/统计负控制，复用同一物理样本，不新跑GPU；其他7个profile各六动作、6进程，共 **252 GPU phase**。COMMON_PRIME 未改控制使用同块S2对应结果，不额外重复以择优。

必须区分：payload改变不应改变地址本身；label改变不能偷偷改变地址；base shift是真地址变化，其失败限制旧规则的坐标适用域，**不证明物理NUMA不存在**。

### S4：诊断开销与真正部署基线（1.5 h）

保留旧 N/T/M/P 的含义，只替换为共同数值体的 DIAG0/DIAG1 配对。scope=FULL，sizes=2/32MiB，HOT one-pass/repeat4，六进程。
- N：一个全设备kernel，64 CTA；中性布局/自然region顺序。
- T：两个匹配组，不搬布局，按固定 parity 类执行；输出物理region。
- M：相同资源匹配、既有可逆着色布局；不增加本轮新算法。
- P：与M完全相同输入布局，只反转计算归属。

每形态4策略×2诊断版本，共 **192主phase**；每case/block加N_DIAG0首尾锚，另48，总240。
每policy独立同配方 warmup，不在每次consumer前增加人工primer。consumer使用32CTA/group、1 visit，repeat4只是显式复用因子。

主比较：T0/N0、M0/T0、P0/M0；旧式诊断只用于同条件差分，不与旧批次绝对时间相减。报告：
`delta_diag = log(P1/M1) - log(P0/M0)`，不把它直接解释成某一条SASS的独立成本。

T和M在均匀归约中读相同的地址集合；它们即便打平也不说明“NUMA必然没用”。真正物理匹配证据来自S2/S3。

### S5：解释、现成少量profile、恢复和交付（0.25 h；CPU分析另计）

最多4次现成profiling：两个冻结大小的T/P，优先无扰动时间线检查是否实际重叠，其次受支持cache/traffic指标。没有工具/权限则NA，禁止安装或为此停止整份报告。Nsight replay/flush/serialization不能冒充原执行条件。

完成结果矩阵和下面的判定；恢复原硬件控制配置，保护动作不能被恢复覆盖。剩余0.5h仅为已指定修复、资格和记录，不用于找新mask。

## 5. 什么情况自行处理，什么情况真正需要人

正常构建、索引、句柄、有限同步修复在预算内自行完成；当前scope不支持、单项NA、负结果或缺counter，都继续其他指定实验。
错误输出隔离当前变体，不将它混入性能；不得为通过而放宽整数相等合同。新device-lost/Xid/热或风扇故障停止GPU并一次汇报，CPU总结继续。

权限/付费/修改driver和固件/改变研究合同才需集中请求。你就运行在T10本机，离线；不SSH、不下载、不试图访问第二台。

## 6. 最终交付要直接回答

1. 固定旧mask和SM集合，在新轮次、新分配上是否复验？
2. 四格交互为正、为零还是反向？每个原始格是什么？
3. isolated CELL 的预测与 JOINT 实测是否一致？
4. 从L8→L1→H1哪里发生变化？是否已排除“只改变总工作量”的误解？
5. owner切换后，地址偏好是否跟着primer走？payload/label/base变化分别怎样？
6. 无诊断kernel是否真正没有读取SM/clock或写诊断？正式图的计算/准备节点各多少？
7. 相对N、T和反向匹配，clean路径是否存在净效应？
8. 功耗/时钟状态是否可比？哪些超界或不稳定块保留了？
9. 支持的是物理NUMA、稳定经验亲和、缓存/并发条件性规律还是仍未知？
10. 是否有必要再谈真实应用？本轮不自动部署渲染/CSR/LLM。

最终文件：`T10_NUMA_FROZEN_RULE_MECHANISM_REPORT.md`，附 `PHYSICAL_VS_EMPIRICAL_CLAIMS.md`、数据与代码manifest、简短导师稿。**不要只交结论或只交热图。**

没有3%/5%作为省略实验的门槛。本轮924个主/锚phase是条件齐备时的上限，不要求把6小时花满。按S0→S1→S2→S3→S4→S5连续执行；预算将满时优先保留S2/S3四格和S4无诊断主比较，不新增S1诊断或profile，未跑给理由；不静默缩短主要计时后维持原样标签。
