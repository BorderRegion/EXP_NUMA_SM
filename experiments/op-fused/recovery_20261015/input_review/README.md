# OP-FUSED T10 审阅包 — 2026-10-15

入口：`REVIEW_T10_OP_FUSED.md`。
给Codex：`CODEX_T10_IMPLEMENTATION_RECOVERY.md`，简短入口 `COPY_TO_T10_CODEX.txt`。
导师说明：`MENTOR_UPDATE.md`。

`independent_audit.py` 是新编写的只读CPU核查，不导入上传runner、不使用CUDA、不联网。
`independent_audit.json` 给出清单、统计、PTX文字、程序适用域和已披露源码快照差异的核查边界。
`paired_recalculations.json` 是从所附逐case phase数据复算的效应；`graph_and_cost_by_case.json` 是从原始Graph树重新提取的所有54个case结构及比值。
`source_evidence/` 只复制本次主要引用的原文件和4个代表性raw，不包含完整原附件、权重或GPU二进制。源材料未修改。

## 重做独立CPU复核

使用已具备Python和NumPy的环境：

```bash
python independent_audit.py --input /path/to/OP_FUSED_T10_REVIEW_AND_BASELINES_20261015 --output /path/to/new_cpu_review
```

不要把本审阅目录当成原始GPU实验根目录。GPU结果未在本环境重新执行，实际输入/输出tensor未附，数值通过率来自所保存的检查摘要。

本次没有另做互联网文献/API查证；后续设计建议与附件原事实在正文中分开标注。
