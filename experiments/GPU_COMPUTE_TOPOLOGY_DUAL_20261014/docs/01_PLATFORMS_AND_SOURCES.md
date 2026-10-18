# 平台事实、推论与外部研究边界

资料核对日期：2026-10-14。来源 URL 只是出处，不要求离线 Codex 访问网络。

## 1. RTX 5070 Ti：裁剪不等于 16.7% 可恢复性能

**已核对的规格（S1 附录 B）：** 完整 GB203 为 7 GPC / 42 TPC / 84 SM。RTX 5070 Ti 为 6 GPC / 35 TPC / 70 SM，L2 = 49,152 KB，显存 16 GB。相对完整芯片少 14 个 SM，即 16.67%。

**规格推论（不是实测）：** 如果每个活跃 GPC 最多 6 个 TPC，那么 35 个 TPC 分到 6 个 GPC，只能是 5 个 GPC 各 6 TPC、1 个 GPC 5 TPC，即每组 12/12/12/12/12/10 个 SM。
- 不知道哪个逻辑 SM 属于哪个 GPC，也不知道具体的调度限制。
- 14 个少的 SM 可以这样理解：1 整个 GPC（12 个 SM）被关闭，另一个 GPC 少 1 个 TPC（2 个 SM）。
- 整个 GPC 缺失的 12 个 SM 是**容量缺失**，调度无法找回。
- 6 个活跃 GPC 相对 6×12=72 只少 2 个 SM（2.78%）。

这意味着：如果把相同的工作平均分给 6 组，10 SM 的那组可能拖慢尾部；但原生按 SM 分发 block 可能已经处理好了这种不均衡。这是**要测量的基线**，不是默认存在的损失。

**表述等级必须分开使用：** 厂商 SKU 总量、实卡 query 结果、cluster 同 GPC 共现、推断出的完整图、带宽经验类结论。不能混为一谈。

## 2. Tesla T10：不能写死规格

用户提供 16 GB 设备。S3 官方 GDN 页面把 T10 列为 Turing，但不同的部署方式或虚拟化可能暴露不同资源。
必须通过 CUDA query 得到：实际名称、compute capability、SM 数、L2、显存、驱动版本、虚拟化与共享进程情况。

- 不使用零散商家规格写死 SM 数，也不假设它没有裁剪。
- 主 CUDA 公共子集可用 `sm_75`（前提是实际确认）。
- cluster 记为 NA。缺少这个新特性不能算作调度器失败。
- CUDA 13.0 移除的是 Maxwell/Pascal/Volta 的离线编译支持，并不包括 Turing。仍以本机工具的实际支持为准（S7）。

## 3. 公共功能的正确理解

**Thread Block Cluster**（cc 9.0 引入）：同一 cluster 内的 SM 共现，可以提供“同 GPC”关系的证据。但**没有共现不能证明不同 GPC**。
核查分四层：源码或头文件、属性查询、实际的小型 launch。`k=1` 的普通 launch 不是独立的 GPC 归属证据。应用本身没有 cluster 需求时，不强行加入。

**Green Context**：CUDA 13.2 文档说明，7.x/8.x 按 2 SM 粒度对齐，9.0 及以上常按 8 SM 对齐。但实际参数必须通过 query 得到。
- 分组是不透明的选择，不支持任意挑选逻辑 SM 列表。
- 没有并发前进的保证，因此不做跨组的 spin 等待。
- 新文档可能比本地 ABI 更新。不猜测 enum 值，也不下载替换。

**`%smid`**：只表示读取那一刻的执行位置，不能假设它连续或跨调度稳定。
相同 SM、相同 GPC 中的服务差异，都不能自动归为 NUMA。

## 4. 最接近的研究（必须比较，不能复述）

- **S2**：Fan 等，*Dissecting How Die Scaling Breaks GPU Fine-grained Scheduling*，arXiv:2609.24270v1。原作者用 cluster 共现和 L2 竞争恢复拓扑，研究 floorsweeping、内存非均匀性和调度，主要实卡为 H200 与 B200。其 §5（大 cluster 可用的 SM）和 §7.4（等量资源、不同分配的讨论）与本课题直接相关。把原方法复现到新卡上属于**复现或工程**，不能声称是首次。
- **S8**：*Enabling and Exploiting Flexible Task Assignment on GPU through SM-Centric Program Transformations*，ICS 2015。静态或以 SM 为中心的任务分配不是新概念。
- **S9**：OO-VR，ISCA 2019。NUMA 渲染中的资源共享、任务分组与均衡已有研究。本课题在单 GPU 应用和软件约束下的具体差异需要明确写出。
- **S10**：CUDA Graphdeco rasterizer 是 W1 的起点，但不保证它是最快的后端。如果本地可用的 gsplat 或其他优化 renderer 与语义设置一致，则加入为生产对照；不可用时记录为 `BASELINE_GAP`。

## 5. 来源索引

- **S1** NVIDIA RTX Blackwell GPU Architecture。PDF 印刷页 49、51–53，已核对页面图像：https://images.nvidia.com/aem-dam/Solutions/geforce/blackwell/nvidia-rtx-blackwell-gpu-architecture.pdf
- **S2** 主论文：https://arxiv.org/abs/2609.24270 ；HTML：https://arxiv.org/html/2609.24270v1 。重点阅读 §5、§7.4。不保证其代码已开源。
- **S3** NVIDIA GDN 规格：https://www.nvidia.com/en-us/solutions/design-and-simulation/gdn-stream-3d-apps/
- **S4** CUDA 功能表：https://docs.nvidia.com/cuda/cuda-programming-guide/05-appendices/compute-capabilities.html
- **S5** Green Context（CUDA 13.2）：https://docs.nvidia.com/cuda/archive/13.2.0/cuda-driver-api/group__CUDA__GREEN__CONTEXTS.html
- **S6** CUDA 程序模型：https://docs.nvidia.com/cuda/cuda-programming-guide/01-introduction/programming-model.html
- **S7** CUDA 13.0 release notes：https://docs.nvidia.com/cuda/archive/13.0.0/cuda-toolkit-release-notes/index.html
- **S8** 原论文参考文献 [6]。第一轮按来源追溯，未在本包中全文复现。
- **S9** https://arxiv.org/abs/2001.03537
- **S10** 固定的参考上游：https://github.com/graphdeco-inria/diff-gaussian-rasterization/tree/59f5f77e3ddbac3ed9db93ec2cfe99ed6c5d121d
- **S11** PTX：https://docs.nvidia.com/cuda/parallel-thread-execution/index.html
- **S12** Nsight Compute 的 profiler 计量限制：https://docs.nvidia.com/nsight-compute/ProfilingGuide/index.html

## 6. 查重状态与边界

完整的文献查重尚未完成。Codex 只读本地副本和本文件，不主动上网。缺少全文的文献记入 `LITERATURE_GAPS`，不能用“没有搜到同名题目”来判断新颖性。
本节的硬件与 API 事实来自外部来源。其余的计划、阈值和方法都是本包的新设计。
