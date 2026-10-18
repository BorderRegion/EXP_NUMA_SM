# 05 来源、推导和未验证的部分

## 源材料支持的事实（不是本轮新运行）
- `T10_SELECTIVE_REORDER_RESULT_20261017.zip`：已实现lazy native、成熟P/R与三partition/two方向；选择器全LIB；卡跨过程类别不稳定；SINGLE校准与其余动作不同时间。
- `T10_SELECTIVE_REORDER_REVIEW_20261017.zip / REVIEW.md`：119/144首尾变化>5%；约590–1193us的旧绝对margin；stable_sort小堆分配；置乱唯一不同T12没有被原trace覆盖；旧数据事后追加位置动作收益不稳定。
- 相同审阅的 `allocation_free_policy.patch`：保行为插入排序修复。当前包另加BASE/SHAPE不计算资源插值，必须通过CPU等价。

本包没有重新审计旧3298phase或CUDA输出，也没有把旧数据用于训练一个新选择器。只有文件/计划/CPU参考检查在交付前执行，详见VALIDATION_REPORT。

## 本次设计/数学推导
ABBA/BAAB局部配对、log相对目标、单侧无量纲风险、全V覆盖trace、预测差异见证，是本次提出的修正。它们尚未在T10验证；不保证模型一定准、一定开启PC或一定获益。相对误差解决尺度不一致，不自动消除模型失配。

固定资源卡只说明公开组服务/交付关系。单台T10、固定卡特征也可能成为shape再表达。RESOURCE更快不自动证明物理NUMA或SM屏蔽因果；需同机制PC干预支持，而且物理域/remote流量仍可能未知。

## 本次重新核对的官方资料（2026-10-17；本机以已装版本为准）
1. NVIDIA CUDA C++ Best Practices Guide，Timing / profiling：CUDA异步调用与同步边界影响CPU计时，代表性负载与完整成本重要。
   https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/index.html
2. NVIDIA System Management Interface：power limits、lock/reset GPU/memory clocks、支持范围与root要求；请求锁频不替代实际readback，也不能覆盖热保护。
   https://docs.nvidia.com/deploy/nvidia-smi/index.html
3. NVIDIA Nsight Compute Profiling Guide，Clock Control / Cache Control：时钟与replay会改变结果，默认cache处理/串行化可能不同于自然执行，故profile独立。
   https://docs.nvidia.com/nsight-compute/ProfilingGuide/index.html

这里的在线文档不是要求Codex联网或升级。未执行新的相关工作全面查重，不宣称本次选择规则首创或具备会议录用保证。
