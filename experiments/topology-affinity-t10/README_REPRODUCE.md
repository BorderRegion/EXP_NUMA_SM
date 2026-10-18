# T10 真实拓扑与地址调度实验复现

先读 `reports/REPORT.md` 和 `reports/REVIEW_QUESTIONS.md`。默认配对未替换；本次未达到地址特异净加速门槛。`reports/DECISION.json` 是机器可读决定。

完整包包含本轮全部原始记录和实际使用的二进制。SM 映射来自本机驱动的 GET 查询，非延迟聚类。小包仅用于阅读和评审，不能独立重算原始实验。

## 纯 CPU 复算

在完整包的 `topology-affinity-t10` 目录执行：

```bash
OPENBLAS_NUM_THREADS=2 /home/ubuntu/projects/leetgpu-lab/.venv/bin/python3 src/recompute.py
```

其他电脑可用已有 Python 3.12、NumPy、pandas 运行同一入口，例如 `python3 src/recompute.py`。记录版本：Python 3.12.3、NumPy 2.5.3、pandas 2.3.3。画图另需 matplotlib；复算不导入 torch 或 CUDA，也不启动 GPU worker。

脚本首先验证 `FILE_MANIFEST.json`，恢复 `FILE_TIMES.json` 中的纳秒时间，然后从原始计时、微测和配对文件重新生成所有统计及审计。派生 JSON、CSV 和数组按语义对比；计算完成后恢复原文件字节与时间，再检查所有包内哈希。gzip 头和图像生成时间不被当作科学结果。

CPU-only 方法不会重新选择最强随机对照，不会改冻结协议。不要使用 `analyze.py fast`：该旧通用入口需要孤立验证矩阵，而快速校准保存的是并发 Latin 数据，原始失败日志已保留。正确入口为 `analyze_fast.py`，已包含在复算流程中。

统计输出：`derived/ALL_OPERATOR_RESULTS.csv` 含全部开发和确认条件；`*_operator.json` 含独立进程效应；`full_summary.json` 为56 SM有向扫描；`NET_RESULTS.json` 为请求块净账单，`NET_SESSIONS.json` 为逐进程汇总；`FINAL_AUDIT.json` 为完整性与数值检查。`ci_primary` 是32比较的保守区间；net 专用族区间字段为 `ci_net_family`，不能混用。

## 原始数据定位

运行号见 `CURRENT_RUN.txt`，各 worker 位于 `runs/<运行号>/`。

- `dev_*`、`confirm_*`：原主实验；`micro/train.bin` 和 `validation.bin` 分离训练与验证。`V*/page*/*/timing.csv.gz` 保留 first、conditioning 和 test。
- `full_*`：全部56×55有向对、三页、两轮，`full_direction.bin` 与 plans 一一对应。
- `shared_*`：同 executable graph 的补充确认，`handles.json`、`graphs.json` 和更新费用均保留。
- `fast_*`：低开销并发校准、短确认和百万请求测试。`micro/latin.bin` 每次launch有28条记录；`latin_permutations.npy` 给出每轮实际配对。
- `fast_*/net/*/b*_*.npy`：每块2048次完整Graph的GPU与host时间，微秒，形状(2048,2)；`chunks.csv.gz` 保存更外层墙钟和独立参数更新时间。
- 各 worker 的 `numerical.json`、`telemetry.jsonl`、`device_before/after.json`、`manifest.json`、日志保留检查、功耗温度与精确源文件版本。ledger 的worker秒包括CPU准备和I/O。

`src/types.hpp` 与 `src/topology_math.py` 定义288字节记录格式。测量是全局邮箱往返，不能按2除后宣称单向物理连线延迟。文件中 GPC 通常是逻辑编号，物理映射在 `support/SM_TO_GPC_TPC.csv`。

## GPU 重测条件

原运行依赖 Tesla T10、56 SM、驱动580.178.04、CUDA12.8、PyTorch2.8.0+cu128，以及100W上限。`src/runtime.py` 会核对拓扑与原快核哈希；`src/worker.py` 使用排他锁和82°C停止阈值。保持保护策略；驱动拓扑变化后不能继续沿用原冻结SM表。

本机 Python 和 CUDA 位于 `/home/ubuntu/projects/leetgpu-lab`。`src/build.py` 记录 probe 的实际编译方法，`build/BUILD.json` 保存完整命令。原快核、copy 和计时帮助库以本次精确二进制保存在 `build/baseline`；对应源码在 `support`。重新编译可能改变二进制与性能，不能替换原包后仍称同一次实验。

CPU帮助库构建逻辑为 C++17、O3、PIC、shared：`fast_fit.cpp` 无CUDA依赖；`shared_graph.cpp` 使用 CUDA12.8 的 `cuda.h` 并链接 `libcuda`。本机匹配头为 `/home/ubuntu/projects/leetgpu-lab/.venv/lib/python3.12/site-packages/nvidia/cuda_runtime/include`；不要优先使用旧的 `/home/ubuntu/projects/leetgpu-lab/cuda/usr/include/cuda.h`。初次旧头编译失败日志保留。

`support/read_topology.c` 使用 NVIDIA open-gpu-kernel-modules 580.178.04 的 `src/common/sdk/nvidia/inc` 与 `src/nvidia/arch/nvalloc/unix/include`，以 gcc GNU11 编译。源来源及哈希在 `support/topology_query_provenance.json`，实际查询程序在 `build/read_topology`。完整厂商源码没有重复装入此包。

新GPU运行应复制到独立目录，分配新run、重新冻结协议与实现，再按 qualification、开发、冻结随机、确认的顺序执行；原 `campaign.py`、`resume.py`、`run_shared.py`、`run_fast.py` 是历史执行脚本，不要在当前交付目录直接重跑，以免覆盖冻结文件。快速阶段后处理应改用新格式分析器，并在新的实现清单中记录该变更。

## 费用边界

net主指标是各请求块外层墙钟之和，加候选完整校准和所有测得的参数更新；对照免准备费用。块间研究落盘、共同Graph创建和每块两次conditioning不在账单内。它保留了完整算子开销，但不是一条真实LLM服务从初始化到最后token的不间断墙钟。不得把该结果改写为整模型tokens/s提升。
