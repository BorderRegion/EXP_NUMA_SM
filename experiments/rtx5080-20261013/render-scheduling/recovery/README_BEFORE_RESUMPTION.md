# RTX 5080 rendering scheduling V2

状态：**BLOCKED_LOCAL_RESOURCE**；路线 C / `CPU_OR_MICRO_ONLY`。本次完成新盘点、19项输入文件完整性核验、20项CPU测试和资源受阻报告。GPU实验尚未开始。

- [主报告](reports/RTX5080_RENDER_SCHEDULING_REPORT.md)
- [缺失资源与恢复条件](reports/LOCAL_MISSING_RESOURCES.md)
- [贡献卡](reports/CONTRIBUTION_CARD.md) / [导师短稿](reports/SUPERVISOR_BRIEF.md)
- [机器可读结果](results/derived/CAMPAIGN_RESULTS.json)、[全部策略](results/derived/ALL_POLICY_RESULTS.csv)、[计划/实际矩阵](results/derived/EXPERIMENT_MATRIX.csv)
- [预算](reports/BUDGET_LEDGER.md) / [记录](WORKLOG.md) / [文件索引](artifacts/CONTENT_INDEX.json)

run_id：`v2_20261013T072225Z`。旧项目在父目录，内容未修改。附件原文保存在 `preregistration/RTX5080_RENDER_SCHEDULING_V2/`；里面的“已授权”“已核实”是提供者声明，不独立构成权限或本次实测证据。

从本目录复算CPU计划与查看记录：

```bash
python3 -B preregistration/RTX5080_RENDER_SCHEDULING_V2/tools/plan.py check configs/campaign.json
python3 -B -m unittest discover -s preregistration/RTX5080_RENDER_SCHEDULING_V2/tests -v
python3 -B tools/summarize.py
```

上述命令不运行GPU。`tools/inventory.py --output <新路径>`可重新盘点；输出必须是新文件。新环境/新资产应建立新的run_id；未存在renderer时不能将source template称为可运行baseline。
