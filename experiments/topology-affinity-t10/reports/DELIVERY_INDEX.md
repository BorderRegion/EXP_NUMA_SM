# T10 拓扑与地址亲和调度交付索引

本轮实验已完成。真实同TPC有小幅孤立邮箱往返优势，但尚未建立地址亲和调度本身的可靠净加速。原默认配对保留。

- 阅读结论：[REPORT.md](REPORT.md)。
- 重点质疑：[REVIEW_QUESTIONS.md](REVIEW_QUESTIONS.md)。
- 数值、拓扑和完整性审计：[FINAL_AUDIT.json](../derived/FINAL_AUDIT.json)。
- 全部算子对照：[ALL_OPERATOR_RESULTS.csv](../derived/ALL_OPERATOR_RESULTS.csv)。
- 固定请求数净账单：[NET_RESULTS.json](../derived/NET_RESULTS.json)。
- 重算说明：[README_REPRODUCE.md](../README_REPRODUCE.md)。

下载目录交付：

- `T10_TRUE_TOPOLOGY_AFFINITY_20261018.zip` 为完整包，包含本轮全部原始记录、实际使用二进制、源码、协议、日志、报告与图。
- `T10_TRUE_TOPOLOGY_AFFINITY_20261018_SMALL.zip` 为网页版GPT评审小包，含报告、质疑、全部条件汇总、协议、源码和图；不含逐次原始大文件和二进制，不能独立重算。

打包后的大小和SHA256在本地 `reports/DELIVERY.json`。CRC、逐文件哈希及完整包独立解压纯CPU复算结果在本地 `reports/ARCHIVE_QA.json`，复算完整日志为 `reports/ARCHIVE_RECOMPUTE.log`。这些文件在完整包生成之后产生，避免完整包记录自身哈希的循环；小包内带有完整包QA结果。完整包内部的 `FILE_MANIFEST.json` 可独立验证所有收录文件。
