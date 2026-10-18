# 交付索引：T10 完整通信尾部与地址放置

- `REPORT.md`：全部主对照、成本账单、分解、适用边界与诚实结论。
- `REVIEW_QUESTIONS.md`：供网页版GPT/同行质疑的具体问题。
- `DECISION.json`：机器可读的判定与原基线保留状态。
- `NET_PRIMARY.png`、`DECOMPOSITION.png`、`MODEL_TRANSFER.png`、`SETUP_COST.png`：审阅图；同名PDF便于导出。
- `../derived/NET_RESULTS.json`：所有候选/对照、外层墙钟/GPU/host指标、逐进程结果、95%和保守区间。
- `../derived/NET_SESSIONS.json`：每进程每方案成本明细。
- `../derived/SHORT_RESULTS.json`、`MICRO_VALIDATION.json`：完整短测与通信微测的不同证据层。
- `../derived/SELECTED_PLANS.json`、`POLICY_CHOICES.json`：所有选择，含重复对照。
- `../derived/MODEL_TRANSFER.json`、`ARRIVAL_DIAGNOSTICS.json`、`STATIC_RULE_TRANSFER.json`：描述性诊断。
- `../derived/TIMING_TAILS.json`与`POSTHOC_DIAGNOSTICS.json`：看完结果后对全部108条件的长尾核查，未删除观测或改主指标。
- `../derived/AUDIT.json`：冻结、数值、Graph、原始记录与功耗温度审计。
- `ENGINEERING_NOTES.json`：两个初期失败与一次未确认中断，未被删除。
- `../freeze/`、`../src/`、`../support/`、`../build/`：协议、实现、原核与新微测、官方拓扑查询来源。
- `../runs/20261018T084714Z/`：全部原始数据、worker日志、失败和未完成记录。
- `../README_REPRODUCE.md`：无GPU独立重算方法与GPU复现边界。
- `../FILE_MANIFEST.json`：完整包逐文件SHA256；`ARCHIVE_QA.json`和`DELIVERY.json`为包生成后的外部校验记录，不纳入完整包自哈希。

完整包：`/home/ubuntu/下载/T10_TOPOLOGY_TAIL_PLACEMENT_20261018.zip`。

网页版GPT小包：`/home/ubuntu/下载/T10_TOPOLOGY_TAIL_PLACEMENT_20261018_SMALL.zip`；包含报告、质疑、全部派生汇总、图和源码/协议，不含逐次原始数据与二进制，不能独立重算。实际字节数、SHA256与校验状态以 `DELIVERY.json` 为准。
