# 来源、已有工作与不能过度声称的地方

核查日期2026-10-13。以下主来源由任务设计时在线核对；实验Codex仍本机离线。只读本地已有论文/文档；链接用于溯源，不是运行时下载授权。以下概括不替代全文，不声称已完成系统性查重。

## S0 用户实验来源
`RTX5080_RENDER_SCHEDULING_RESUMED_REPORT.md`，run `resumed_20261013T0930Z`；Graphdeco commit `59f5f77e3ddbac3ed9db93ec2cfe99ed6c5d121d`。
实际旧结果是CPU辅助Q分包方案没有净收益，位置×区域交互、物理控制未建立。旧资源受阻报告已被恢复阶段超越，不能再次假定工具链和资产全无。当前计划不得篡改旧raw或把它们并入新结果。

## S1 原论文：已有静态NUMA分配
Xiaoze Fan et al., *Dissecting How Die Scaling Breaks GPU Fine-grained Scheduling*, arXiv:2609.24270v1, 2026-09-21。
https://arxiv.org/html/2609.24270v1
https://arxiv.org/pdf/2609.24270
重点：§6、§7.1、§7.4.1、Appendix C/E/F；PDF第8和14页核对过图与附录。
论文已用静态任务分配、persistent blocks和数据本地化。附录物理地址方法需要驱动改动，不能搬到普通虚拟地址；论文的硬件结果不直接覆盖5080。本题若只是复现静态分配，是工程验证而非新颖方法。论文页内会议模板文字不作为录用状态证明。

## S2 CUDA 13.2 Green Context（与本机版本优先对齐）
https://docs.nvidia.com/cuda/archive/13.2.0/cuda-driver-api/group__CUDA__GREEN__CONTEXTS.html
公开SM资源分组与stream执行可用性需本机query；这不是任意物理SM绑核。disjoint SM也不保证任意kernel并发前进，故不允许跨组busy wait。

## S3 当前在线Locality Domains（不能冒充本机已有）
https://docs.nvidia.com/cuda/cuda-programming-guide/04-special-topics/locality-domains.html
当前文档提供locality domain查询、localized compute与memory接口。单域也可以合法返回；本机13.2有无声明/符号/支持需独立核对。不能升级、猜enum整数或认为5080必须有多个domain。

## S4 CUDA执行模型和PTX位置寄存器
https://docs.nvidia.com/cuda/cuda-programming-guide/01-introduction/programming-model.html
https://docs.nvidia.com/cuda/parallel-thread-execution/index.html#special-registers-smid
block执行与SM分配不按block编号提供固定保证；smid是观察值，可能非连续且可能因重调度变化。因此本轮按实际roster和资源组定义匹配，不能按blockIdx“绑SM”。

## S5 Cooperative Groups
https://docs.nvidia.com/cuda/cuda-programming-guide/04-special-topics/cooperative-groups.html
标准grid同步必须满足对应cooperative launch与容量条件。只允许支持且实际资格通过的用法；不仿制普通grid自旋barrier。

## S6 Graphdeco evaluator与上游
https://raw.githubusercontent.com/graphdeco-inria/diff-gaussian-rasterization/59f5f77e3ddbac3ed9db93ec2cfe99ed6c5d121d/cuda_rasterizer/forward.cu
https://raw.githubusercontent.com/graphdeco-inria/diff-gaussian-rasterization/59f5f77e3ddbac3ed9db93ec2cfe99ed6c5d121d/cuda_rasterizer/rasterizer_impl.cu
完整tile的计算与其有序candidate列表有关；上游逐相机生成列表。只改变完整tile分配，不能把相机变化下的资源关联静态不变当成事实。

## S7 已有NUMA渲染与调度
Chenhao Xie, Xin Fu, Mingsong Chen, Shuaiwen Leon Song, *OO-VR: NUMA Friendly Object-Oriented VR Rendering Framework For Future NUMA-Based Multi-GPU Systems*，原ISCA 2019工作，arXiv:2001.03537。
https://arxiv.org/abs/2001.03537
已涉及NUMA渲染、资源共享与工作分配；多GPU/模拟平台与本机单GPU不同，但“换应用+常规分组均衡”不构成充分新意。

## S8 相关表征与3DGS任务调度
*DGNA: Dissecting GPU NUMA Architecture through Microbenchmarking and Data Analysis*, arXiv:2607.19922v1。
https://arxiv.org/abs/2607.19922
*CaT-GS: Efficient 3DGS Rendering for Large Scale Scenes via Inter-frame Caching and Tile Scheduling*, arXiv:2607.17842v1。
https://arxiv.org/abs/2607.17842
本包只用于提示必须比较的相邻研究，不据标题推断全部算法/接口；缺全文保留unknown。普通tile调度与亲和表征不是空白。

## S9 Profiling
https://docs.nvidia.com/nsight-compute/ProfilingGuide/index.html
replay/序列化/cache处理会改变cache-sensitive实验。正式timing与profiler分开；proxy和闭源counter不可得的限制明列。

## 新增方法应达到什么边界
本轮的候选首先是标准静态分配与特化的机会原型。paper主张需进一步证明：真实不规则多资源共享与负载变化产生已知简单策略无法处理的约束；初始化代价/映射有效期可控；新规则在独立输入上有增量，并有拒绝/失效行为。正收益、首次在5080复现或constexpr替换表读都不自动满足新颖性。
