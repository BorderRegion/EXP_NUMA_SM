# T10 限定收束实验

先读 `CODEX_MASTER_TASK.md`。任务的GPU接入由本机Codex在现有工程完成。

CPU工具示例：

```bash
python3 tools/make_resource_sets.py --csv /path/to/current/SM_TO_GPC_TPC.csv --output freeze/resource_sets.json
python3 -m unittest discover -s tests -v
```

`support/HISTORICAL_SM_TO_GPC_TPC.csv` 只是来源于上一轮用户附件的历史快照，不可以当作当前硬件已经绑定的证明。`choose_prefix` 和 `graph_schedule` 只验证固定请求序列，不会运行CUDA。

主任务限定240分钟总墙时、90分钟GPU-worker，并受上一轮余额约束。不要为花满预算重复测试，不自动衔接新的大实验。
