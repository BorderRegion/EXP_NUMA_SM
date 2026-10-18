# 本轮复现与边界

先读 `reports/REPORT.md` 和 `reports/REVIEW_QUESTIONS.md`。本轮是独立冻结的后续验证，不覆盖上一轮原始记录，也不默认启用实验性 SM 地址映射。

完整包包含本轮所有原始计时、输入哈希、图结构、数值检查、遥测、冻结规则/映射、代码和二进制。小包用于网页版 GPT 审阅，省略原始计时及二进制，不能据它独立复算全部结果。旧映射的训练原始数据属于上一轮 `T10_SM_AFFINITY_SOFTMAX_20261018.zip`；本轮携带冻结矩阵及映射，不声称重新测量了完整拓扑。

纯 CPU 复算（依赖 NumPy）：

```bash
CUDA_VISIBLE_DEVICES='' python3 src/recompute.py
python3 src/stability.py
```

原机 Python：`/home/ubuntu/projects/leetgpu-lab/.venv/bin/python3`。
编译参数、编译器/CUDA 路径在 `build/causal_build.json`；编译辅助依赖 `lgjudge.cudabuild`。包不包含整套 CUDA SDK。

实验 API 为 `src/runtime.py` 的 `Data(V, seed)` 和 `Job(data, slot, variant, policy, page, scope)`。它是受控实验夹具，不是成熟推理引擎接口；仅在这台 56-SM T10、经过 roster/occupancy 检查的资源配置下验证。`Job.run()` 返回完整 GPU/主机计时，`Job.check()` 验证输出，`Job.close()`/`Data.close()` 释放资源。共享 workspace 的不同 Job 必须串行运行。勿在原 run 目录内重跑；worker 对已存在目录拒绝覆盖。

主结果不包含 profiler 指令；`diagnose` 的插桩版本仅验证工作分布、归并者与粗粒度阶段，不可用其绝对时间冒充正式内核时间。所有收益均需对照完整旧快核，均衡布局、固定归并、普通融合自身的收益不计为地址亲和收益。
