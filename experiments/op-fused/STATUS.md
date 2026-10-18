# OP-FUSED T10 — 算子内实现与有限矩阵完成

状态：**SAME_CORE_GAIN_ONLY / MATH_BACKBONE_GAP**。FULL 已实现，原预算内的条件分支已完成；不是仍在等源码。

468 个 case-block、5544 个含锚 phase、82116 条正式数值检查全部通过；六轮 grouped/control 与六轮 post-route 层测试完整。

主 grouped：FULL/LIB=2.0335，FULL/CACHE=0.8536；层 F1S1/LIB=1.8340，F1S1/F1S0=0.9098。FULL 冻结 qcap=1，与 ABL 完全 alias；保留同体正效应，不将其归因于新包长信息。融合增量未明确。

累计 GPU-worker 5.4695/16 小时，本轮新增 2.1890 小时。固定 100 W，风扇/过温/低转速/watchdog 保护保留。

从 implementation/reports/OPERATOR_FUSED_IMPLEMENTATION_REPORT_t10.md 和 QUESTIONS_FOR_PAPER_REVIEW.md 开始复核。轻量包在 exports/OP_FUSED_T10_IMPLEMENTATION_COMPLETE_20261015.zip。

旧原生报告、raw 和包保留；旧 STATUS 副本在 implementation/reports/PRIOR_STATUS_native_baseline.md。attention 新候选、动态路由和真实模型为本轮缺项，不能当成已完成结果。

## 2026-10-16 同 q 接续（v2）

新任务已完成，旧报告与冻结保留。状态：`implementation_same_q_v2/20261015T171030Z/RUN_STATE.json`；新协议、源码和原始数据均单独记录，沿用原账本与 GPU 锁。

本轮 28 worker、2,010 phase 全部完成；新增 GPU-worker 0.8937 小时，累计 6.3632/16 小时。主报告：`implementation_same_q_v2/20261015T171030Z/reports/T10_SAME_Q_AND_BACKBONE_REPORT.md`。当前无待执行实验。
