# 环境与能力盘点

日期：2026-10-13，Asia/Shanghai。run_id：affinity_20261013T064931Z_b2cdc88d。
证据为 results/raw 同run目录的 environment_sandbox.json 和 environment_host.json。
主机盘点时间为14:51:34；显存/温度/使用率为瞬时快照。

| 项目 | 实际结果 | 证据/含义 |
|---|---|---|
| OS | Ubuntu 26.04 LTS，Linux 7.0.0-38-generic，x86_64 | /etc/os-release、platform |
| GPU | NVIDIA GeForce RTX 5080；1个设备 | 主机 cuDeviceGetName/Count成功 |
| GPU UUID | GPU-b864b6c3-6dad-2596-5e83-3b15d32a13b5 | 主机 nvidia-smi设备级查询 |
| 驱动 | 595.99.02 | nvidia-smi与内核版本 |
| CUDA driver兼容版本 | 13020，即13.2 | cuDriverGetVersion；不代表toolkit安装 |
| 计算能力 | 12.0 | cuDeviceComputeCapability成功，非网上型号推测 |
| nvidia-smi总显存 | 16303 MiB | 包含驱动保留范围 |
| CUDA设备可报告容量 | 16608133120 bytes，即15838 MiB | cuDeviceTotalMem_v2成功；与smi口径不同 |
| free / used | 15026 / 814 MiB | 14:51瞬时值，不作为后续分配许可 |
| 温度 | 40°C | 只读快照；未做负载健康测试 |
| GPU / memory utilization | 3% / 15% | 显示活跃，非独占 |
| 实际SM数 | UNKNOWN | 无本地官方属性枚举header，未硬编码查询 |
| 观测smid范围 | NOT_MEASURED | 无kernel启动 |
| L2容量 | UNKNOWN | 未查询、未实测，不猜测工作集大小 |
| nvcc / ptxas / cuobjdump / nvdisasm | 在PATH及盘点常规目录中未找到 | 无小CUDA kernel构建环境 |
| NVIDIA CUDA headers | 未找到 | /usr/include/linux/cuda.h是Apple微控制器接口，不能误用 |
| nsys / ncu | 未找到 | profiler不足，不冒充计数可用 |
| cmake / ninja / gcc / g++ / python3 | 已有 | 本轮CPU工具仅用Python标准库 |
| CUDA renderer / 资产 | 搜索范围内没有候选 | 见资源表，不推断未搜索磁盘不存在资产 |

## 公开接口能力

| 候选能力 | header检查 | runtime/device结果 | 能否断言不支持 |
|---|---|---|---|
| CU_DEVICE_ATTRIBUTE_LOCALITY_DOMAIN_COUNT | 官方cuda.h缺失 | NOT_QUERIED | 否 |
| Green Context locality-domain group | 官方头/字段缺失 | NOT_QUERIED | 否 |
| CU_MEM_LOCATION_TYPE_DEVICE_LOCALITY_DOMAIN | 官方cuda.h缺失 | NOT_QUERIED | 否 |
| pointer/allocation locality属性 | 官方声明未核验 | NOT_QUERIED | 否 |
| thread-block cluster | 未检查官方header/设备属性 | UNKNOWN | 否 |

没有硬编码枚举、复制其他架构地址公式或查询物理地址。
cuInit在沙箱内返回100 / CUDA_ERROR_NO_DEVICE，沙箱外返回0 / CUDA_SUCCESS。
所以初次失败来自设备可见性隔离；不能写成主机无GPU或驱动损坏。
两次获准的沙箱外动作仅为只读盘点，不构成系统安装/权限改动授权。

## 搜索边界和现有作业

盘点 /home/ws/work、/home/ws/文档/ChatGPT、/home/ws/下载、/home/ws/公共、
/usr/local、/opt、/usr/include、/usr/share/doc及常规CUDA目录；文件名匹配
*.cu、*.ply、*.splat、*.pt、*.pth、SOURCES_AND_SCOPE.md、cuda_runtime.h、nvcc。
/home/ws/work 下 projects/data/results 初始为空；本项目初始无源码/结果。
不访问浏览器/账号/密钥目录、不扫描其他进程内存、不访问远程平台。
GPU显示活跃，存在桌面负载；未终止任何现有进程，未启动旧campaign。

## 安全容量准备

以本次快照计算探测上限min(512MiB,15026MiB×10%)=512MiB；实际申请0。
应用保守保留ceil(16303MiB×15%)=2446MiB，快照下资产空间最多12580MiB，
实际资产/分辨率尚未冻结；正式运行需重新查询并检查完整renderer峰值。
缺L2容量，0.25/0.75/1.5/4倍L2测试尚无法具化，不能自行猜测。
