# OP-FUSED T10 接续交付

先读 `reports/OPERATOR_FUSED_IMPLEMENTATION_REPORT_t10.md`，然后看 `reports/MUTABLE_CORE_RESOURCE_REQUEST.md`。

本包完成缺资源情况下的 CPU 接口、执行入口修复和资源交接；没有把新方法 GPU 实验标为完成。旧有限基线包继续保留，本包不是其 raw 的替代品。

CPU 复核（从工程根目录执行，不使用 CUDA 设备）：

```bash
python3 op-fused/recovery_20261015/tests/test_contract.py
python3 op-fused/recovery_20261015/tests/test_frozen_source.py
python3 op-fused/recovery_20261015/tests/test_applicability.py
python3 op-fused/recovery_20261015/tools/packet_applicability.py \
  --out op-fused/recovery_20261015/reports/packet_applicability.json
python3 op-fused/recovery_20261015/system/fixed_power.py
```

未来 GPU 入口继续使用 `op-fused/tools/worker.py STAGE UNIQUE_KEY SCRIPT [ARGS]`，预算仍是原 `registry/runs.jsonl`，锁仍是工程根目录 `environment/gpu_worker.lock`。不启动新 baseline-only campaign。源码供应及主体实现完成后，应把新 GPU 脚本纳入 worker 的冻结目录，所有输出显式写入 `--out`，不可写只读快照。

只读代码快照涵盖工程内 source/config/preregistration/protocol/vendor；已安装的 Python/CUDA 动态库不复制，单独记录版本和 hash。CPU 测试不证明外部库在运行期间不可变。
