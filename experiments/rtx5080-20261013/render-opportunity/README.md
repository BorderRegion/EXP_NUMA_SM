# GPU affinity rendering campaign

本轮状态：**BLOCKED_LOCAL_RESOURCE**。实际设备RTX5080，缺离线CUDA开发工具链、
测量runner、renderer/资产和文献；GPU kernel/session均为0。
E0、CPU准备和资源受阻分支E6已完成，未宣称硬件阴性或渲染收益。

从 [主报告](AFFINITY_RENDER_OPPORTUNITY_REPORT.md) 阅读结果；
恢复要求见 [集中资源表](reports/LOCAL_MISSING_RESOURCES.md) 和
[唯一准备包](artifacts/MINIMUM_VALIDATION_PACKAGE.md)。

预注册在preregistration/，环境和全部SYNTHETIC自检在results/。
tools/仅为离线盘点和CPU分析工具；10项自检通过，不能代替GPU/renderer证据。
manifest.json记录全树hash；归档在artifacts/。raw不覆盖，恢复后新建run_id。
