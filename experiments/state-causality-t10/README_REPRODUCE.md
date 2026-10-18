# T10 运行状态与请求节奏诊断复核说明

本包是 2026-10-17 的有限后续诊断；主报告为 `reports/T10_STATE_CAUSALITY_REPORT.md`。保留每次尝试、conditioning、原始请求时间戳、NVML 查询区间、独立 CUPTI 活动、程序快照和预算账本。没有新增 NUMA 算法。

## 从原始数据离线复算

需要 Python 3.10+ 与 NumPy；解压到一个新目录，在包根目录执行：

```bash
CUDA_VISIBLE_DEVICES='' python3 recompute.py
```

脚本先核对 `MANIFEST_SHA256.json` 的全部文件，再重新运行 CPU 分析，并与交付的 `derived/results.json`、`derived/profiles.json` 比较。它不导入 Torch、不调用 GPU、不联网、不依赖旧工程目录。浮点数比较容差为绝对 1e-7、相对 1e-10。验证程序会重写解压目录中的两份派生 JSON，因此请保留原 ZIP 或使用新解压副本。

重新画图还需要 Matplotlib：`python3 src/figures.py`。PNG 用于阅读，PDF 用于排版。报告生成还依赖包内已完成的 FINAL_AUDIT.json，不能在另一台机器把 final_audit.py 当作离线复算程序执行。

## 文件与口径

- `freeze/PROTOCOL.json`：主协议；`LOW_OBSERVER_CONFIRMATION_ADDENDUM.json`：预先登记的低频复验。较早协议版本与修改理由也保留。
- `runs/<run>/ledger.jsonl`：所有 worker 的实际时间、状态、源文件/二进制哈希。失败尝试计费计时，不纳入成功正式测量的统计。
- `runs/<run>/raw/<worker>/source_snapshot.zip`：该 worker 启动时的实际源码，不以最后源码覆盖历史。
- `condition.requests.csv.gz` 与 `phase_*.requests.csv.gz`：所有请求；`phases.jsonl` 为阶段边界和宿主时钟锚。conditioning 不丢弃，但不混入正式阶段。
- `telemetry.jsonl`：每次查询的起止时间及 NVML 返回码；采样频率不等于设备传感器刷新频率。累计 violationTime 是 ns，referenceTime 是 us。
- `phase_*.packets.json`：BURST64 整包计时。异步单请求没有可观测的 host-ready 时间，该字段留空，不能从整包均分伪造。
- `graphs.json`、`correctness.jsonl`：图身份、节点、地址与数值验证。
- `activity.chrome.json`：最多两次独立的 CUPTI 捕获，不能替代正式 wall time。
- `derived/results.json`：原始重建、阶段统计、按进程块的探索性 bootstrap。主 6 块、控制 2 块、监测器 2 块和低频确认 2 块分开报告。
- `derived/profiles.json`：不拟合时移的活动归属、完整/缺失单位与 kernel 参数。缺失原样保留。

B/C 的完成率包含主动等待、事件读取和循环开销，不能只看单请求变快。D 与 READY 的主可比量是实际完成率。相邻 A 的几何均值是参照口径，不保证消除了历史漂移。小样本区间只作探索性描述，不代表普适置信保证。

## 环境与重跑边界

本机 Tesla T10、固定 100 W；保留风扇及过温保护。直接设置时钟被系统拒绝；硬件缓存计数器受管理员权限限制。此包没有锁频对照或缓存根因证据，也不能证明物理 NUMA。

包内 GPU 数学 cubin 与前轮保持一致；只增加宿主端节奏与记录。GPU 重新编译/运行依赖原 CUDA、PyTorch、CUTLASS 环境及前轮输入目录，且当前预算已经结算，不能直接用本包启动队列续跑。CPU 复算是独立可移植的。前轮交付 ZIP 的哈希和源文件对照列在 freeze/PRIOR_HASHES.json 与 reports/FINAL_AUDIT.json；本包不重复前轮大批 raw。

独立解压复算结果及本包 SHA-256 见外部 `reports/DELIVERY_INDEX.md`（避免把 ZIP 自身哈希循环写进 ZIP）。
