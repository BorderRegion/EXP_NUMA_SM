# 设计时来源核对与论文差异

核对日期：2026-10-13。以下是设计阶段的外部核实；Codex执行时不访问链接。采用本地已有论文、headers与代码，缺全文的地方标明。此页不是穷尽查重。

## 一、硬件／API事实

**S1 NVIDIA RTX Blackwell GPU Architecture v1.1**，附录B，PDF第49–51页（0基48–50）。5080/GB203参考规格：84SM、64MiB L2、16GB GDDR7、960GB/s。它没有证明我们的5080应用具有NUMA瓶颈。
https://images.nvidia.com/aem-dam/Solutions/geforce/blackwell/nvidia-rtx-blackwell-gpu-architecture.pdf

**S2 NVIDIA RTX5080产品页／CUDA GPU列表**：产品页列compute capability12.0。具体工具链是否支持、第三方扩展是否包含兼容代码，仍需本机确认。
https://www.nvidia.com/en-us/geforce/graphics-cards/50-series/rtx-5080/
https://developer.nvidia.com/cuda/gpus

**S3 Blackwell Tuning Guide**：区分cc10.0与12.0的occupancy及shared memory；不能把B200资源限制直接代入5080。
https://docs.nvidia.com/cuda/blackwell-tuning-guide/index.html

**S4 CUDA Driver API 13.4 在线数据类型与Green Context文档**：存在locality-domain相关查询/分配/SM组名称；本机可能没有。Green Context的disjoint SM仍不保证任意kernel并发/前进。单域设备的域0内存池不意味着创造了新物理域。
https://docs.nvidia.com/cuda/cuda-driver-api/cuda_driver_api/group__CUDA__TYPES.html
https://docs.nvidia.com/cuda/cuda-driver-api/cuda_driver_api/group__CUDA__GREEN__CONTEXTS.html

**S5 PTX ISA special register smid**：返回读取时执行位置，编号可稀疏，可能因抢占/重调度变化；不是placement API。
https://docs.nvidia.com/cuda/parallel-thread-execution/index.html

**S6 Nsight Compute Profiling Guide**：默认replay可能清缓存并序列化。cache-sensitive结果需要核对本地replay/cache配置，不应直接使用孤立冷cache指标解释自然应用。
https://docs.nvidia.com/nsight-compute/ProfilingGuide/index.html

## 二、与原论文的关系

**P1 Dissecting How Die Scaling Breaks GPU Fine-grained Scheduling**，arXiv:2609.24270v1。已读正文和相关附录；设计核对了§6.2/§7及图7/8。论文已研究硬件结构和拓扑/NUMA-aware调度；其结果涵盖H100/H200/B200等，并将5090列为monolithic L2。未报告5080测试。
https://arxiv.org/abs/2609.24270
https://arxiv.org/html/2609.24270v1

本轮复用的是“先区分可测硬件现象，再研究可控调度”的思路。不是直接复现论文所有驱动／物理地址方法；不套用其物理页XOR映射，不把用5080换机器视作新论文。

## 三、渲染与调度的近邻

**P2 OO-VR: NUMA Friendly Object-Oriented VR Rendering Framework For Future NUMA-Based Multi-GPU Systems**，ISCA 2019，arXiv:2001.03537。已经研究NUMA渲染中的资源共享与负载分配。我们是当前单卡CUDA软件路线，但仅更换硬件/应用名称不构成新增方法。B5提供共享分组＋均衡机制对照，不冒充原系统完整复现。
https://arxiv.org/abs/2001.03537

**P3 CaT-GS**，arXiv:2607.17842v1，2026-07。已读§3.4、实现与相关质量说明。含跨帧机制和tile负载处理；其某些路径采用分段alpha重结合与近似跨帧计算。本轮保持单像素原计算顺序，因此不能直接把其全系统与本方法称为bitwise同合同。仍必须正面讨论其负载均衡贡献，不能说tile scheduling首次出现。
https://arxiv.org/html/2607.17842v1

**P4 3D Gaussian Splatting for Real-Time Radiance Field Rendering**，TOG2023；官方CUDA reference的renderCUDA是每block处理tile、每thread处理像素，并按有序列表读取属性与合成。
https://repo-sam.inria.fr/fungraph/3d-gaussian-splatting/
https://raw.githubusercontent.com/graphdeco-inria/diff-gaussian-rasterization/main/cuda_rasterizer/forward.cu

**P5 gsplat**：当前公开CUDA rasterization项目与文档，作为可用现代baseline候选。不能默认本地已经存在，也不能把不同raster mode、抗锯齿、剔除和输出合同混写成公平同算法比较。
https://github.com/nerfstudio-project/gsplat
https://docs.gsplat.studio/main/

**P6 普通locality-aware scheduling／ray排序／work stealing**：存在长期前人；本轮的资源摘要、LPT、空间排序和贪心合并都不是单独新概念。正式研究需要进一步核实最接近的缓存容量约束任务分组方法。本次定向网络检索没有建立完整先例排查，不能写“首个联合调度”。

## 四、创新与证据分离

| 观察或实现 | 不能自动声称 | 真正需要追加的证据 |
|---|---|---|
| 5080出现热图差异 | 新NUMA节点 | 位置×数据交互、复验、合法可用控制 |
| Morton后更快 | 新调度算法 | 必须与成熟空间顺序比较 |
| Q比原生快 | 拓扑/缓存因果 | matched队列、load、feature置乱、cap消融 |
| B5与M都快 | M的论文贡献 | M是否超出B5、为什么、在哪些独立输入成立 |
| 三个3DGS场景有收益 | 通用infra泛化 | 仍只有一个renderer；需另程序外部验证 |
| 5%加速 | 能投某顶会 | 新方法、机制、可复现、强基线、适用范围 |

## 五、范围承诺

本包没有包含第三方PDF全文、外部模型或下载脚本，只有来源定位与有限转述。离线执行不要求在线重新查文献；已有资源不足时统一报告，设计者/导师后续可以完成外部查重，不能让Codex反复触发网络申请。
