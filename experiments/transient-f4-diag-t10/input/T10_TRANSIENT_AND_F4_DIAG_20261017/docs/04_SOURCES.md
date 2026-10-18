# 来源与推断边界

## 用户提供证据

- `T10_SELECTIVE_REORDER_REPAIR_V2_REPORT.md`（本轮旧报告）：AA 102/168超过5%；真实trace/FFN退化、V14/V15/V16选SINGLE；100W动态，无管理入口；本机完整raw路径应从CURRENT_RUN/索引确认。
- `paired.py`、`pair_runtime.hpp`、`pair_suite.py`：conditioning/窗口/夹具差异。只读副本与来源hash在evidence。
- `deployment_v2.py`、`deploy.py`、`runtime_extra.hpp`：请求选择、FFN第一动作、共享LIB第二层、Graph和等待。
- 前一独立审阅`AA_position_diagnostics.json`：BEGIN/END模式基于小包聚合顺序推断。本轮D0要用本地显式raw重验，不当成已经定位的物理原因。

本包新增的因子实验、请求级计量、预算和确认顺序均为新设计，不是旧报告已经证明的事实。证据副本仅用于定位，不能替代实际本机源码/二进制核对。

## 本次外部核对（2026-10-17，官方一手文档）

O1 CUDA Runtime API 13.2 Event Management：
https://docs.nvidia.com/cuda/archive/13.2.0/cuda-runtime-api/group__CUDART__EVENT.html
支持点：事件记录异步且后续记录会覆盖状态；完成与elapsed计算分开；context/stream要正确；事件跨度不保证纯kernel时长。实验采用本机Driver API时须按其实际同等语义核对，不照搬Runtime函数名。

O2 CUDA Best Practices Guide：
https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/index.html
支持点：CPU计时必须与异步GPU工作完成边界相配；CPU/GPU计时与有效带宽口径需分开。本轮不假设一个计时协议能消除状态变化。

O3 NVIDIA System Management Interface：
https://docs.nvidia.com/deploy/nvidia-smi/index.html
支持点：功耗/时钟变更有设备支持与权限范围；实际读数/限制要记录。不是保证锁频会解决本次异常。

O4 Nsight Systems User Guide：
https://docs.nvidia.com/nsight-systems/UserGuide/index.html
支持点：现有CUDA/Graph活动与API时间线可辅助定位，捕获及观测开销须按工具实际功能记录。不要求T10安装新工具。

上述文档没有证明本次AA的根因，也没有提供T10物理NUMA结论。本轮不需要联网下载资料，URL只是来源线索。
