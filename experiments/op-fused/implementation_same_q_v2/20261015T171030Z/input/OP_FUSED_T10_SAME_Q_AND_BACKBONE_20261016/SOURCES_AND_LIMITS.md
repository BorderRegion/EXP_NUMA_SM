# 来源与使用边界

## 本次主要依据

用户附件 `OP_FUSED_T10_IMPLEMENTATION_COMPLETE_20261015.zip`。本包 `evidence/source/` 保留关键报告/源码原样副本；逐run计时仍在原附件。副本来源见文件清单。未加载.so、未运行GPU、未重算未附带tensor。

## 外部有限核实（2026-10-16）

仅为技术解释和补充任务提供背景，不替代本机能力测试，不要求Codex联网。

1. NVIDIA Turing Tuning Guide：32 resident warps/SM、64KB shared memory等架构上限；不能把这些上限当achieved occupancy或直接根因。
   https://docs.nvidia.com/cuda/turing-tuning-guide/index.html
2. NVIDIA CUTLASS Grouped Kernel Schedulers：device-only和host-precompute、persistent tile调度、排序未必更快。在线页面4.7.0，而本机源码pin为3.5.1，必须以本地接口为准，不按在线新API重装。
   https://docs.nvidia.com/cutlass/4.7.0/media/docs/cpp/grouped_scheduler.html

本次不是完整新颖性检索。没有证明“精简q1 visitor”或“融合SiLU和multiply”为新技术，默认按对照/工程实现。即使获得加速，也需要额外方法与独立证据才能升级为论文主张。
