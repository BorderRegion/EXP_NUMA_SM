# 来源、已知事实与本轮假设的分界
核对日期：2026-10-16。以下是本次设计时外部核查的摘要，不表示离线Codex已在本机取得全文。研究执行不需联网。

## 本对话已给出的证据
E0 `T10_SAME_Q_AND_BACKBONE_REPORT.md`：q1是普通N-panel遍历，没有物理SM/NUMA干预；计算主体仍有库差距。不能把这些结果迁移成NUMA方案的成败。
E1 `T10_SUPPLEMENT_AND_PAPER_POSITION.md`：地址相关受顺序影响；部分同执行器正效应未胜原生；cache/DRAM服务未测。这是现象和限制，不是已识别的物理domain。
E2 `thermal_controller_source.json`：历史service名t10-quiet-fan.service，100/125W及温度/转速触发已记录；本轮必须核对当前实现，不机械照抄阈值。

## 外部主来源
**S1 — Dissecting How Die Scaling Breaks GPU Fine-grained Scheduling，arXiv:2609.24270v1**
https://arxiv.org/html/2609.24270v1
https://arxiv.org/pdf/2609.24270v1
核对§6、§7.1、Appendix C/E以及PDF第6、8、14页图示。作者分开研究裁剪与内存非均匀性；静态放置、persistent执行、地址重映射及推理kernel集成都已有。Appendix E的无LUT算术建立在物理连续分配/物理基址条件上；不可把公式直接用于本机VA。该论文的设备证据不自动适用于T10/5070Ti。引用版本为预印本，不根据模板里的会议日期或占位DOI宣称录用。

**S2 — NVIDIA System Management Interface**
https://docs.nvidia.com/deploy/nvidia-smi/index.html
power limit受设备报告min/max约束；请求clock与实际clock须读回，功能按设备支持。用户授权覆盖T10运行控制，不覆盖超频、改驱动和取消保护。最终由本机已安装工具的接口为准。

**S3 — PTX ISA：%smid、cache operator**
https://docs.nvidia.com/cuda/parallel-thread-execution/index.html
smid是读取时的执行位置，不保证连续或跨抢占固定；cache operator不是物理数据home接口。普通/cg服务层必须用测量解释，不能将cg等同于必到DRAM。

**S4 — CUDA Driver API 13.2 Green Contexts**
https://docs.nvidia.com/cuda/archive/13.2.0/cuda-driver-api/group__CUDA__GREEN__CONTEXTS.html
公开计算资源分区；组ID不提供内存域含义，不保证任意跨组并发。只使用本机头文件/库真实支持的入口，不猜ABI。

**S5 — Nsight Compute Profiling Guide**
https://docs.nvidia.com/nsight-compute/ProfilingGuide/index.html
replay/cache-control会影响缓存敏感实验；代表性profile与主计时分开。指标无法获得则按缺项报告，不把proxy换名为counter。

**S6 — CUDA Locality Domains（当前在线版）**
https://docs.nvidia.com/cuda/cuda-programming-guide/04-special-topics/locality-domains.html
在线规范提供计算和内存共同域标识及fork/join与Graph范式，但本机13.2或特定OS未必提供该接口。页面还限制Windows/vGPU/MIG等情境。这里只用于解释理想公开控制合同；不得为采用它自行升级系统。

**S7 — CUTLASS grouped schedulers**
https://docs.nvidia.com/cutlass/4.7.0/media/docs/cpp/grouped_scheduler.html
库已有grouped device/host调度与问题顺序优化；保留成熟主体和同信息基线，不能将一个普通visitor改名为新NUMA算法。

**S8 — OO-VR（ISCA 2019；arXiv版本2001.03537）**
https://arxiv.org/abs/2001.03537
已有NUMA渲染的共享与工作分配；不同硬件实现可以构成研究约束，但仅换工作负载不是创新。

**S9 — NVIDIA Matrix Multiplication Background**
https://docs.nvidia.com/deeplearning/performance/dl-performance-matrix-multiplication/index.html
算术强度和shape影响瓶颈；roofline只是近似筛查。不能说LLM必然memory-bound，也不能用一个shape推断所有推理。

## 本轮新假设，不是上述来源已证明
在本机实际存在可复验亲和的前提下，能否把有限的布局/执行规则编译进成熟kernel或前序producer，消除per-task LUT，并在动态不规则负载与全成本下获得现有静态方法之外的增量。

目前没有完整的新颖性证明。实验中保留最近的简单静态NUMA方法、普通locality+balance、成熟生产库；如果新方案与它们等价，说明复现/工程价值，不制造论文差异。
