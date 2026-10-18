# 复算与阅读

优先阅读 `reports/REPORT.md` 与 `reports/REVIEW_QUESTIONS.md`。本轮完整尾部/放置实验不覆盖前一轮真实分组RTT原始数据；硬件拓扑、查询源码与来源另附在 `freeze/` 和 `support/`。

完整包可在无GPU环境重算全部派生JSON/CSV。需要Python3、NumPy、pandas；画图另需Matplotlib。不依赖Torch，不需要CUDA或本机原绝对目录。

```bash
cd topology-tail-t10
OPENBLAS_NUM_THREADS=2 python3 src/recompute.py
```

脚本检查文件SHA256、冻结实现、拓扑、数值、通信原始记录、132候选覆盖、Graph顺序、BLIND选择来源、全部长测数组和统计；从原始数据重新生成派生文件，进行语义比较后还原原字节及mtime，最后再次核验整个包。不会重选BLIND或启动GPU。小包不包含原始数据与二进制，不能执行这项复算。

图可用 `python3 src/figures.py` 重新生成。报告生成器为 `src/report.py`。渲染文件可能因库版本而不同，不作为原始性能证据。

GPU实际执行记录在 `runs/20261018T084714Z/*/manifest.json`、`ledger.jsonl` 和日志；关键源码和二进制在 `freeze/IMPLEMENTATION.json` 固定。初版失败和中断也在包内。正式原快核的来源文件在 `support/baseline_softmax_const.cu`，其二进制被逐字节保留；新微测、诊断和Graph参数更新编译命令在 `build/BUILD.json`。编译工具路径是原机器环境，移机需配置本地CUDA12.x、兼容驱动、PyTorch CUDA与host compiler；原工具助手路径在 `src/build.py`，不是可移机直接调用的通用安装器。

如需GPU复现，请另建独立实验目录/新run，保留本包只读，复制当前protocol与原二进制后记录新硬件环境和时间。入口 `src/campaign.py`/`resume*.py` 是本次历史执行与恢复程序，会生成freeze并要求新worker目录；**不能在本已完成目录直接重跑**。定点racecheck只覆盖新tail核1次launch；不要把本轮中断的全量racecheck当作通过。100W上限和82°C停止规则是本轮条件，不修改风扇或过温保护。

本机原实验Python：`/home/ubuntu/projects/leetgpu-lab/.venv/bin/python3`。净耗时包含实测请求块、调参更新、预热与候选校准；不包括共同构图、首次上下文/编译、输入分配和研究落盘。统计独立单位是6进程，不能把请求数当样本数。
