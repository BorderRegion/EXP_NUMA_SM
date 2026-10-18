# 来源与研究边界

## A. 用户已经提供的本机事实
这些是用户报告，不是本包重新执行的GPU数据：
- `T10_NUMA_FROZEN_RULE_MECHANISM_REPORT.md`：旧0x33有局部低并发效应，物理NUMA未确证；不涉及真实LLM partial生产链。
- `T10_SAME_Q_AND_BACKBONE_REPORT.md`：本地已有可修改CUTLASS数学基础，普通/Grouped对库仍有差距；q1只改遍历而非物理位置。
- 历史温控脚本记录：100/125W自动切换与风扇/温度保护。以当前文件实际版本为准。

## B. 本次设计时核查的公开第一手资料（2026-10-16）
来源链接供追溯。实验Codex默认离线，不能把这些链接当成联网要求，也不能只看摘要就声称完整复现。

S1 NVIDIA CUTLASS, Efficient GEMM in CUDA。
https://docs.nvidia.com/cutlass/latest/media/docs/cpp/efficient_gemm.html
支持：parallel split-K使用部分GEMM和独立batched reduction，workspace为必要中间输出；适合输出tile不足的场景。它已是现有技术。

S2 NVIDIA CUTLASS, GemmSplitKParallel implementation。
https://raw.githubusercontent.com/NVIDIA/cutlass/main/include/cutlass/gemm/device/gemm_splitk_parallel.h
支持：可核查P/R的参数和发射边界，典型FP32工作区约sizeof(acc)*M*N*S。默认模板类型不代表T10最优。在线main不是本地commit。

S3 Tri Dao等，Flash-Decoding for long-context inference，PyTorch，2023-10-13。
https://pytorch.org/blog/flash-decoding/
支持：KV分段生产局部输出和归一化统计，再做最终归并；经典路径有两个实质kernel。该设计本身不是本研究新贡献。

S4 FlashInfer官方仓库、attention API与decode实现。
https://github.com/flashinfer-ai/flashinfer
https://docs.flashinfer.ai/api/attention.html
https://raw.githubusercontent.com/flashinfer-ai/flashinfer/main/include/flashinfer/attention/decode.cuh
支持：项目声明覆盖SM75及更新架构；每种具体split/merge接口仍以本地源码与运行资格为准。不能从项目支持推断所有kernel可用。

S5 Osama等，Stream-K: Work-centric Parallel Decomposition for Dense Matrix-Matrix Multiplication on the GPU。
https://arxiv.org/abs/2301.03598
https://arxiv.org/html/2301.03598v1
支持：已有跨CTA partial交付与时序/工作分解设计，kernel内部调度与降低fixup代价都不是空白。必须作为近邻，不能只引用名字。

S6 Dissecting How Die Scaling Breaks GPU Fine-grained Scheduling。
https://arxiv.org/html/2609.24270v1
支持：区分计算裁剪与访存非均匀性，并已将资源/内存位置用于算子和LLM场景。其H200/B200的物理映射前提不能直接套T10；本包不是对其创新保证。

S7 CUDA13.2 Green Context官方API。
https://docs.nvidia.com/cuda/archive/13.2.0/cuda-driver-api/group__CUDA__GREEN__CONTEXTS.html
支持：公开资源分区与限制；不重叠SM组不保证任意kernel并发/前进性，实验不能靠跨组忙等。

S8 Turing Tuning Guide。
https://docs.nvidia.com/cuda/turing-tuning-guide/index.html
支持：实际Sm75能力与资源基准；不要套Hopper DSM/TMA/wgmma/tcgen的实现。

S9 nvidia-smi官方文档。
https://docs.nvidia.com/deploy/nvidia-smi/index.html
支持：功耗/时钟需设备支持与权限，requested上限不等于恒定实际频率；保留保护和恢复。

## C. 本包新增但待验证的设计
P×C×workspace反事实、相同数学/融合的PC匹配、无新增调度pass的slab/短规则，是本轮设计，不是上述资料已证明在T10上有效。
现有split/merge、静态划分、cache swizzle、Graph和epilogue融合本来就已存在。只有针对真实交付路径的信息带来同等条件下独立增量，才有资格讨论新方法；且还需正式related-work比较。
没有物理计数时可以报告受控经验PC效应，但不宣称屏蔽让几何邻SM距离变远、远端流量减少了多少或破解了内存home。
