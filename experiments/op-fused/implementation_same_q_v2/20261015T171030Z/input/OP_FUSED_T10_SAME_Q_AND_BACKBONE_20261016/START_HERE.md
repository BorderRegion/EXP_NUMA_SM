# T10 OP-FUSED：同 q 归因与高效主体恢复

设计／审阅日期：2026-10-16。输入是 `OP_FUSED_T10_IMPLEMENTATION_COMPLETE_20261015.zip`，其结果和失败保持原样。

本包不是新选题，也不是恢复旧 Green/NUMA 计划。它针对本次实际实现中的三个问题：正式 FULL 退化为 q=1、缺少同 q 简单基线、同体主体远慢于生产库。

阅读顺序：`REVIEW.md` → `CODEX_6P5H_TASK.md` → `EXPERIMENT_CONTRACT.md` → `campaign.json`。

本轮规划工作量约6.5小时，硬上限7小时；是给Codex的顺序工作预算，不是完成保证。GPU-worker最多4小时，且不能超过原16小时账本剩余额度。CPU开发、编译、分析与GPU等待都进入本轮工作墙时；不能把6.5小时另算成纯GPU运行再无限开发。

直接在T10现有工程中实施；本机离线、不重装、不下载、不改100W及原保护。旧报告已记录此前另行授权的源码下载和功耗调整，本包不追溯否定，但不重复执行。

正常工程修复、去重、有限参数冻结与分支连续完成；终点是 `T10_SAME_Q_AND_BACKBONE_REPORT.md`。不要逐小步等待审阅。

证据包只含本次审阅所用的小型源码和报告副本及CPU复算，不含完整vendor源码／模型／GPU输入张量，不可声称已在本环境执行GPU。`evidence/independent_audit.py` 可用Python+NumPy对原附件解包目录重新计算，本包不需要重新复制原9.6MB附件。
