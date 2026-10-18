# T10 统一准备流程复验：复核说明

先读 `reports/T10_MATCHED_PACING_REPORT.md`。这是一轮有限的 A/B 节奏复验，保留原始请求、预热、固定空闲准备、遥测查询区间、数值检查与实际程序快照。

## 离线 CPU 复算

使用 Python 3.10+ 和 NumPy，在新解压目录的包根执行：

```bash
CUDA_VISIBLE_DEVICES='' python3 recompute.py
```

先核对全部 manifest SHA-256，再从原始压缩 CSV 与遥测重建 `derived/results.json`，与交付结果逐项比较。浮点容差相对 1e-10、绝对 1e-7。脚本不导入 Torch、不创建 CUDA 上下文、不联网，也不需要旧工程目录。它会重写解压副本中的派生 JSON，请保留原 ZIP。

重新画图需要 Matplotlib：`python3 src/figures.py`。四张 PNG 和同版 PDF 已交付。

## 主要目录

- `freeze/PROTOCOL.json`：四块实验的预登记流程。监测1/20/20/1Hz；每块固定180秒空闲、30秒conditioning、8秒×5窗的ABABA；完全相同的输入。
- `freeze/EXECUTION_SOURCES.json`：启动smoke前冻结的执行源码哈希。
- `freeze/BINARY_HASHES.json`：从前轮原样复制的 backend.so 与两个数学 cubin。
- `runs/<run>/ledger.jsonl`：所有成功/失败worker实际耗时及状态。
- `runs/<run>/preparation/block_*`：固定空闲期间的遥测、设备客户端快照、起止时间。无CUDA上下文、无GPU-worker锁保留，墙钟单列；不把它悄悄删掉或混进GPU执行时间。
- `runs/<run>/raw/<worker>`：每条请求的begin/context/launch/ready/event-read时间、图身份、连续global request与槽位、所有conditioning及测量阶段。
- `fixture.json`：四槽输入和权重的字节哈希；`graphs.json`：实际图/函数/grid/block与资源配置；`correctness.jsonl`：完整FP32参考与预定FP64子块验证。
- `telemetry.jsonl`：每个NVML字段的起止时间、返回状态；20Hz只密集查时钟/原因，完整功耗温度计数约1Hz。
- `source_snapshot.zip`：每个worker启动时的真实源码，不能用最后源码代替历史版本。
- `derived/results.json`：阶段统计、100ms描述桶、逐B对照、逐进程汇总和监测层比较。
- `support/PREVIOUS_SUMMARY.json`：前轮结果摘要；前轮完整ZIP与原始数据的身份由冻结哈希引用，本包不重复旧raw。

## 比较口径

A为原连续READY0，B为同样请求完成后请求sleep100us。实际间隔不假定等于100us；完成率包含等待和全部宿主循环开销。每次B与相邻两个A的几何均值比较，再将两次B结果汇总为一个进程块。两个B共享中间A；每个监测条件仅两个进程，不能将请求数或窗口数伪装成更多独立样本。本轮不报告请求级置信区间。

所有预热和阶段记录都保留，未丢弃阶段开头、极端值或不利结果。快慢650/850us界线仅沿用前轮描述，不用于筛选或调度。相同准备流程不保证所有隐藏硬件状态都相同。

## 边界

旧主协议包括C（1000us等待）和D（BURST64），本轮是A/B专项复验。因此新旧百分比之差不能被当成纯监测频率效应。只有本轮四块之间统一了其余指定流程。

固定100W、风扇和过温保护保持；没有改变GPU时钟。锁频及硬件缓存计数器缺少权限，未执行成功。本轮没有证明物理NUMA、冷热全矩阵、其他GPU客户端完全隔离或自适应优化的泛化收益。

GPU重跑依赖原CUDA/PyTorch/CUTLASS与前轮输入目录，需要新目录与预算；不要在已结算队列上直接重跑。`final_audit.py`包含原工作区与设备校验，属于本机结算程序，不是可移植离线复算入口。

ZIP自身哈希、独立解压QA及交付索引保存在包外，避免自引用哈希；见原工作区 `reports/DELIVERY_INDEX.md`。
