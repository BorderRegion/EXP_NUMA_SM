# 来源、新颖性与离线执行

本方案设计日：2026-10-15。作者在设计时核查了下列主来源；**Codex实验仍离线**，本包摘要不是全文副本、不是本地已读或已复现证明。在线文档变化时不自动升级本地工具。没有完整系统查重，不声明first。

## 来源表
- **[S0] T10_SUPPLEMENT_AND_PAPER_POSITION.md**（user-provided experiment report；2026-10-15）
  本对话已提供的本机实验报告，旧目录只读引用。
  旧T10 W1 E/N≈1.0903、M/R≈1.0012；ca-GrQc全设备自写正效应被分区代价吃掉。此为该报告的数据，不是本次新测量。
- **[S1] CUTLASS Grouped Kernel Schedulers**（official documentation；retrieved 2026-10-15）
  https://docs.nvidia.com/cutlass/4.7.0/media/docs/cpp/grouped_scheduler.html
  已有persistent grouped kernel、device-only及host-precompute、K排序与其局限。必须作强基线。
- **[S2] Accelerating MoEs with a Triton Persistent Cache-Aware Grouped GEMM Kernel**（authors on PyTorch official blog；2025-08-18）
  https://pytorch.org/blog/accelerating-moes-with-a-triton-persistent-cache-aware-grouped-gemm-kernel/
  已有persistent与L2/cache-aware grouped GEMM。不能将同expert/panel分组直接称首创。
- **[S3] Stream-K: Work-centric Parallel Decomposition for Dense Matrix-Matrix Multiplication on the GPU**（research paper；2023）
  https://arxiv.org/abs/2301.03598
  已有针对GEMM波次/量化损失的工作分解。仅支持其能力时列对应基线，不新加split-K到本轮主候选。
- **[S4] FlashInfer: Efficient and Customizable Attention Engine for LLM Inference Serving**（research paper；2025）
  https://arxiv.org/html/2501.01005v1
  已有动态attention调度与plan复用等设计；本轮不能只凭不等长任务+调度声称新颖。
- **[S5] FlashInfer repository and attention API**（official project/docs；retrieved 2026-10-15）
  https://github.com/flashinfer-ai/flashinfer
  当前仓库列SM75及之后，但具体功能需本地核查；引用在线支持范围不是本地已可执行证据。
- **[S6] CUTLASS Blackwell functionality**（official documentation；retrieved 2026-10-15）
  https://docs.nvidia.com/cutlass/latest/media/docs/cpp/blackwell_functionality.html
  所述GeForce SM120 GEMM路径cluster为1×1×1，不能照搬SM100大cluster参数；文档针对该kernel路径，不外推所有功能。
- **[S7] CUDA Graphs**（official documentation；retrieved 2026-10-15）
  https://docs.nvidia.com/cuda/cuda-programming-guide/04-special-topics/cuda-graphs.html
  Graph与真正kernel fusion不同；主比较要给基线同样的合法capture/replay条件。
- **[S8] Dissecting How Die Scaling Breaks GPU Fine-grained Scheduling**（research preprint；2026-09-21 v1）
  https://arxiv.org/html/2609.24270v1
  原文已研究Attention/MoE与资源不对称；换到LLM不自动形成新贡献。
- **[S9] Mirage Persistent Kernel**（research preprint；2025; v2 2026）
  https://arxiv.org/html/2512.22219v2
  已有跨算子megakernel编译与runtime。本轮不重写全模型megakernel，融合也不能单独称新颖。
- **[S10] SonicMoE**（research paper / official implementation；paper 2025; implementation retrieved 2026-10-15）
  https://arxiv.org/abs/2512.14080
  已有IO/tile优化；token rounding可能改变路由，不能混入同语义对照。
- **[S11] SonicMoE official source**（official implementation；retrieved 2026-10-15）
  https://github.com/Dao-AILab/sonic-moe
  当前实现列SM120等支持，属于5070Ti可用时的强候选基线，不为离线跑它自动安装。
- **[S12] CUDA Compute Capabilities**（official documentation；retrieved 2026-10-15）
  https://docs.nvidia.com/cuda/cuda-programming-guide/05-appendices/compute-capabilities.html
  架构支持不等同；T10与5070Ti不能强行统一新指令和格式。

## 需要正面面对的近邻
| 已有能力 | 本轮能否据此声称新方法 |
|---|---|
| 单kernel grouped GEMM、host/device调度 | 不能，[S1]已有 |
| 按expert/panel提高cache局部性 | 不能，[S2]已有 |
| 调整tile数量/拆分改善末波 | 不能笼统声称，[S3]已有相关方法 |
| 变长attention均衡、重复plan | 不能，[S4]已有 |
| GPU硬件拓扑与Attention/MoE调度 | 不能只换工作负载，[S8]已研究 |
| 把多个算子放入一个kernel | 不能，[S9]已有且本轮不做全图runtime |
| 减少MoE IO/有效tile浪费 | 不能泛称，[S10/11]是强近邻 |

## 本轮待检验的差异，而非预设结论
1. 有效tile数/worker容量、局部复用包和尾部预算能否共同产生超出固定cache分组/已有动态调度的增量？
2. 在当前动态metadata必须由GPU producer产生的条件下，合法sideband与无物化visitor能否不增加独立调度launch且保留实际收益？
3. 相同策略在grouped与attention上能否迁移；若只在单个shape、单个手工实现有效，应降低主张。

如果所有改动都能一一归入上述已有技巧，保留复现/工程价值，不开发大系统来包装。反之，必须给出一个具体的未解决约束、算法处理方式、负例和独立数据，才讨论下一篇paper。

## 本轮不研究安全缺陷
这是一项授权本机的性能/正确性实验，不进行驱动模糊测试、越权内存访问、网络扫描、故意无效GPU程序或反例漏洞挖掘。正常数值失败按工程资格隔离。
离线执行仅限制实验资源获取，不缩减成CPU mock；缺资源就如实缺项，不能把未实现标成无收益。
