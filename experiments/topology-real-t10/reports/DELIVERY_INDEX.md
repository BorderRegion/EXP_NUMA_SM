# T10 真实核采样交付索引

- `REPORT.md`：全部主对照、校准账单、静态收益和地址特异性的边界。
- `REVIEW_QUESTIONS.md`：供外部审阅的具体质疑。
- `DECISION.json`：机器可读判定和新基线54。
- `NET_PRIMARY.png`、`CALIBRATION_COST.png`、`MODEL_TRANSFER.png`、`PROCESS_OUTCOMES.png`：科学图，提供同名PDF。
- `../freeze/PROTOCOL.json`、`IMPLEMENTATION.json`、`STATIC.json`、`BASELINE_REFERENCE.json`：冻结设计、实现、独立开发静态选择与用户指定基线。
- `../derived/NET_RESULTS.json`：全部口径、寿命、比较、区间及逐进程结果；只有primary字段为true的20项是预定义主比较。
- `../derived/NET_SESSIONS.json`：每方案每进程成本明细。
- `../derived/CALIBRATION.json`、`SELECTION_DIAGNOSTICS.json`：两阶段选择、回退与相同对照。
- `../derived/SHORT_RESULTS.json`、`STATIC_CONTROLS.json`、`MODEL_TRANSFER.json`：短测、静态对照、开发集采样预测力。
- `../derived/TIMING_TAILS.json`、`AMORTIZATION.json`：全部方案长尾和明确标注假设的摊销外推。
- `../derived/BASELINE_REPLICATION.json`：新基线相对旧规则的复验；仅反转既有静态比较方向。
- `../derived/FAMILY_TOPOLOGY.json`、`WORK_DISTRIBUTION.json`：四类配对真实分组与原核每SM工作量。
- `ENGINEERING_NOTES.json`与`ANALYSIS_REPAIRED.log`：CPU JSON序列化修复，原始失败日志和冻结公式保留。
- `../derived/AUDIT.json`：数值、Graph、来源、原始数据和功耗温度审计。
- `../runs/`：全部原始计时、校准数组、数值检查记录、worker清单和遥测。
- `../src/`、`../support/`、`../build/`：执行与纯CPU复算源码、原核/拓扑查询源码、二进制和构建命令。
- `../README_REPRODUCE.md`：复算步骤及GPU重跑边界。

完整包 `/home/ubuntu/下载/T10_REAL_KERNEL_AFFINITY_20261018.zip`。网页版GPT小包 `/home/ubuntu/下载/T10_REAL_KERNEL_AFFINITY_20261018_SMALL.zip`，含全部汇总、协议、源码、图、报告与质疑，不含原始数据/二进制，不能独立重算。

完整包逐文件哈希在 `../FILE_MANIFEST.json`。打包后生成的外部校验记录 `ARCHIVE_QA.json`、`DELIVERY.json` 不纳入完整包自哈希；实际字节数、文件数与校验状态以它们为准。
