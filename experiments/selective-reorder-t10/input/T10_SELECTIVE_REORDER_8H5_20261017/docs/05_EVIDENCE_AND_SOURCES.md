# 依据与未证明事项（2026-10-17）

## A. 用户附件支持的事实

1. `T10_PC_HANDOFF_LLM_REPORT.md`：已实现成熟CUTLASS parallel split-K、实际P→W→C；M=G别名；主方案没有稳定净增量；注意split-KV adapter缺失。
2. `T10_SELECTIVE_REORDER_INTERPRETATION_20261017/ANALYSIS.md`：12已见shape的事后池LIB+CORE约0.937375，加入M/P约0.935729；不是部署结果，仅说明普通实现选择与亲和增量必须区分。
3. 已附src：Resources构造时枚举资源；Engine按mode创建多个组；capture中的kind3/4/0/1已提供大部分动作；数学P/R可复用；formal旧规则只选一个partition/pi。
4. 旧正式矩阵有强制split分箱和宽N开发缺口，不能沿用为本轮生产决策。

本轮新的shape、两级策略、资源profile、ridge/误差阈值、时间预算均是**拟议实验设计**，不是附件已经证明的算法或性能。

## B. 本轮外部核实，仅设计依据，Codex不必联网

- NVIDIA cuBLAS 13.2，算法/描述确定后可重复复用；库存在启发式/计划选择，不把“初始化选择一个算法”称首创。https://docs.nvidia.com/cuda/archive/13.2.0/cublas/index.html
- NVIDIA CUDA Driver 13.2 Green Context：真实资源子集接口；资源不重叠也不保证任意并发/前进性。https://docs.nvidia.com/cuda/archive/13.2.0/cuda-driver-api/group__CUDA__GREEN__CONTEXTS.html
- CUTLASS Efficient GEMM：parallel split-K有partial生产与必要归并；split不适合所有shape。https://docs.nvidia.com/cutlass/4.7.0/media/docs/cpp/efficient_gemm.html
- NVIDIA-SMI：功耗/时钟设置需受支持范围与权限，固定cap不等于实际恒定功耗。https://docs.nvidia.com/deploy/nvidia-smi/index.html
- NVIDIA Matmul Heuristics：已结合shape/硬件选择配置；强形状基线和等额autotune不能遗漏。https://docs.nvidia.com/cuda/nvidia-matmul-heuristics/

当前网络版本只支持技术原则；本机API/ABI以已安装13.2头文件、运行库和实测为准，不猜新枚举，不安装新版本。

## C. 论文不能提前声称

没有因果证据说T10裁剪拉长SM邻接链；没有已确认物理NUMA节点；四个公开组不是四个物理域；单卡选择器胜出不等于跨设备泛化。新方法若仅等于普通shape/runtime autotune，要按工程报告。既有PC信息提供额外价值仍需本轮同动作池和独立输入验证。

本轮8.5小时不做完整相关工作综述，不承诺会议级别。所得程序、记录与新确认可以支持下一步研究判断，但不能把大量phase等同论文成立。
