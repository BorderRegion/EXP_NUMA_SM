# T10 真实GPC竞争与GQA验证

把 `COPY_TO_CODEX.txt` 与本包交给当前T10本机Codex。完整执行合同在 `CODEX_MASTER_TASK.md`。

主线只有一条：历史地址偏好×真实GPC复算 → 等SM配额集中/分散 → 原向量GQA → 全资源有用共置。不是新一轮Softmax配对搜索，也不是同时启动三个课题。

`support/` 是既有记录，原样复制用于明确事实来源。`plans/` 是本次新设计。历史映射不是永久硬件编号。

`tools/build_resource_sets.py` 可以读取本机当前同格式RM CSV，生成六块计划。`plans/HISTORICAL_RESOURCE_SETS.json` 来自历史56条映射，仅为静态核对，没有创建GPU分区。

工具不使用网络、不操作GPU或系统配置。没有附上未测试却声称可用的CUDA性能实现。

验证：
```bash
python3 -m unittest discover -s tools -p 'test_*.py' -v
python3 tools/build_resource_sets.py --csv support/HISTORICAL_SM_TO_GPC_TPC.csv --out /tmp/t10_resource_sets.json
```

正式运行必须使用当前RM读数和已验证的实际资源控制，而不是直接信任历史JSON。
