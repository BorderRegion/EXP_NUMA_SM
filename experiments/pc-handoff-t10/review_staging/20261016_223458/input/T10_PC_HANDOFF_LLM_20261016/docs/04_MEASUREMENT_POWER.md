# 完整计量、功耗、阶段成本与统计

## 1. T10运行控制
用户已批准支持范围内功耗等控制。先保存实际requested/enforced power、支持范围、应用/锁定时钟能力、风扇/过温控制服务与恢复方式。
主条件100W；若本机已选择了合法稳定clock，在不改变内存/热保护前提下固定并读回。没有权限仅记录真实条件并一次性列出具体管理操作，不反复请求、不尝试密码。
旧`quiet-fan`会在80°C/低RPM触发100W，<=70°C与足够RPM后回到125W（历史描述，先读实际版本）。实验期间协调正常目标为100W，保留异常保护；不能让两个控制者轮流改设定。
125W仅E5小型敏感性，支持且安全稳定时执行；100W与125W独立分析，不能给候选125W基线100W。
所有策略受同一保护。出现真正过温、风扇故障、device-lost/Xid时停GPU，保存未完成记录，CPU整理继续。不要关闭watchdog、修改固件或反复跑故障输入。
结束恢复原配置，但不能在热保护仍触发时强制升回高功耗。恢复结果有读回，不只输出命令成功。

每个独立superblock先60秒有用原生算子conditioning；每phase热身按真实路径，不用无用忙等保持温度。1Hz元数据依次采样，保存查询时刻；不称它们为原子读数或实际瞬时功耗恒定。
记录首尾锚>5%作为状态标签不删块，不事后用频率回归生成正收益。

## 2. 三个计时口径
(1) GPU链跨度：同一合法父stream/上下文内的一对事件覆盖P及C（及共同必要操作）。不是所有kernel busy时间的和。
(2) CPU input-ready到结果ready：包含实际Graph/launch/event与必要更新，不包括离线FP64校验/磁盘。
(3) 紧密batch：每次replay仍运行完整P/R，除以次数只叫稳态吞吐时间，不叫ITL/p99。
不能用max(各组event)替代整段makespan，不能减不同SM clock/不同context event。

正式低开销Graph仅用外层事件和必要真实依赖，stage计时在独立代表诊断中插入。不得在P后D2H再启动C。每个producer本轮写出的数据必须是consumer的输入。
所有策略等机会用Graph、预分配、workspace复用和现成fusion。没有图支持时统一matched条件，再单列库最优部署参考。

## 3. 重复与采样
主phase至少32个完整warmup，累计至少100ms；根据开发LIB选择共同replay count达到约50–150ms的batch（16..1024有限范围），所有同case策略同次数。
正式每phase64个独立“提交到ready”请求，以及一次上述batch。每次请求更换预生成输入ring中的槽，热权重可以保留；copy和必要pointer update各策略相同并记账。
第一次/中间/末次输出校验，完整资格单列。计时内无额外hash/clock/SM诊断kernel，不逐请求写大日志。
E2每cell先同P/C暖身，16–64完整PC replay，轮次中的cell顺序平衡；每格输入同样而数据每次由P覆盖。

## 4. 缓存语义
自然主测量：每轮P真实生成partial，不人为flush，不在中间重读热W。
SCRATCH仅反事实：在P与C之间扫描自有内存，其成本并列报告，不能用包含大scratch的总时间掩盖C差异。
R-only若重用partial，标R_ONLY_REUSE；它不是正常P→C通信。
workspace槽换地址保持容量、对齐和内容相同；无法确保物理页独立要明确。
跨case峰值内存影响后面分配时固定分配顺序或同进程共享事先计划的pool；不从最快地址挑结果。

## 5. 覆盖与profiling
DIAG1可记录P和C的实际SM、logical_tile、split id和output owner，不去记录每条load。
DIAG0编译消除SM/clock/trace/ownership原子，只保留算法本来需要的内存操作和数值输出；SASS抽查真实计时入口。
实际空间图是验证布置，不是按逻辑id猜。库不暴露位置时标UNKNOWN，不能给库编造执行组。
本机已有ncu/nsys/CUPTI可用时最多8次采样：低/中/高通信占比、matching/reverse、一个生产库。保留replay/cache-control设置；profile与正式统计分离。没有counter不阻塞全部真实算子实验。
cache/DRAM字节、长依赖stall、occupancy、TensorCore活跃度只报实际工具提供的指标。源码2W不当硬件DRAM流量，CTA并行不当保证全卡饱和。

## 6. 独立单位与分析
E3/E4有8个superblock；每superblock内跑全部既定case，策略使用8行Williams设计，并有LIB首尾锚。共享同一输入/权重和主workspace布局基准；不同policy的地址需求固定，不能冷热条件不同。
bootstrap先以superblock整体抽样（保持同块所有case的共同状态相关），再对固定测试集等权log ratio求均值。不要把所有case×block当彼此无关硬件实验，更不把epoch当独立样本。
逐case区间以及固定族总效果都报；6个层块单独分析，不混入算子总表。
预注册两个主比较M/LIB、M/G，各给97.5%边际区间作为两主对比家族；其余95%探索性，所有正负条件原样展示，不把多张探索图合称整体显著。
阶段成本的比例只能描述观测；用R-only相减推纯通信是禁止的。对位置信息用相同图/布局SASS路径的差分；对融合用四格交互。

## 7. 初始化与回本
分开成本：研究全矩阵、部署必需标定、shape-bin选型、编译/加载、workspace分配、Graph构造和每请求更新。
只用真实部署C_extra + N*T_M 与相同scope的N*T_REF比较。负的稳态收益没有有限回本。
包括额外workspace容量/代码体积；不要将研究全部支持开销当部署开销，也不把研究标定免费抹掉。

## 8. 公共资源限制
单GPU worker，锁实际获得时间与request/start/end分开。CPU编译<=min(4,物理核一半)。
保留max(2GiB,15%实际显存)余量，weights、KV、partial、参考、Graph池和副本都计入。
真实数学kernel由小规模逐步启动，不能为了2ms诊断目标强行拆碎生产数学；长算子按既有安全执行经验确认，不使用永久persistent/busy wait。
软盘空间12GiB、硬限24GiB；二进制和失败保留，原始tensor用可再生成seed/小量快照去重。
