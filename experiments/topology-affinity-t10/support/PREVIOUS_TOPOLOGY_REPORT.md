# 本机 Tesla T10 的 GPC/TPC/SM 屏蔽分布实读结果

检查日期：2026-10-18。结论：**不是逐 GPC 均匀屏蔽。物理 GPC 0–5 的启用 SM 数为 10、12、12、10、0、12。**

本机有效配置为 5 个启用 GPC、28 个启用 TPC、56 个启用 SM。相对完整 TU102 的 6 GPC × 6 TPC × 2 SM = 72 SM，少了 8 TPC / 16 SM。其中物理 GPC 4 整组关闭，物理 GPC 0 的 TPC 0 关闭，物理 GPC 3 的 TPC 5 关闭。

这里的“关闭/屏蔽”表示驱动返回的当前有效 floorsweeping 配置。没有读取制造熔丝，也不能确定每一处关闭是制造缺陷、产品分档还是其他配置原因。未修改屏蔽、驱动、功耗、温控或时钟。

## 实读分布

每个启用 TPC 中有 2 个 SM；其数量同时由完整 SM 映射逐项核对。

| 物理 GPC ID | 启用 TPC 掩码 | 关闭的物理 TPC ID | 启用 SM | 关闭 SM |
|---|---|---|---:|---:|
| 0 | 0x3e | 0 | 10 | 2 |
| 1 | 0x3f | 无 | 12 | 0 |
| 2 | 0x3f | 无 | 12 | 0 |
| 3 | 0x1f | 5 | 10 | 2 |
| 4 | 0x00 | 0, 1, 2, 3, 4, 5 | 0 | 12 |
| 5 | 0x3f | 无 | 12 | 0 |
| 合计 | GPC 启用掩码 0x2f | 8 个 TPC 关闭 | 56 | 16 |

![当前启用分布](/home/ubuntu/文档/ChatGPT/numa_gpu/gpc-mask-t10/reports/GPC_DISTRIBUTION.png)

图只是按编号排列的分布表，**不是芯片平面坐标图**。相邻编号不等于物理相邻，整组关闭也不能直接换算为互联跳数变化。

## 当前全局逻辑 SM 编号属于哪些 GPC

下表合并两种直接返回值：`GR_GET_GLOBAL_SM_ORDER` 给出全局 SM → 逻辑 GPC/TPC；`GRMGR_GET_GR_FS_INFO` 给出逻辑 GPC → 物理 GPC。后者实读为 **0→0、1→1、2→2、3→3、4→5**，不是猜测连续编号。

| 物理 GPC ID | 当前驱动全局逻辑 SM ID |
|---|---|
| 0 | 6, 7, 16, 17, 26, 27, 36, 37, 46, 47 |
| 1 | 0, 1, 10, 11, 20, 21, 30, 31, 40, 41, 48, 49 |
| 2 | 2, 3, 12, 13, 22, 23, 32, 33, 42, 43, 50, 51 |
| 3 | 8, 9, 18, 19, 28, 29, 38, 39, 52, 53 |
| 4 | 无；整组关闭 |
| 5 | 4, 5, 14, 15, 24, 25, 34, 35, 44, 45, 54, 55 |

逐 SM 的逻辑 TPC、TPC 内 SM 编号和物理 GPC 映射保存于 [SM_TO_GPC_TPC.csv](/home/ubuntu/文档/ChatGPT/numa_gpu/gpc-mask-t10/reports/SM_TO_GPC_TPC.csv)。CSV 中 `logical_local_tpc` 保留驱动的逻辑编号，不把它当成物理 TPC 掩码的位号；本次没有建立逐 TPC 逻辑到物理编号的独立映射。

这些是本次驱动/启动状态的编号快照，不承诺跨驱动版本或重新启动始终不变。CUDA `%smid` 本身也不是物理坐标保证。

## 证据与交叉核验

设备：Tesla T10；PCI `0000:01:00.0`，ID `10de:1e37`；`lspci` 标识 TU102GL；UUID `GPU-8cfbc08d-0090-bc29-db9a-b2a2f7261ca5`；VBIOS `90.02.41.00.01`。内核模块及 GSP 版本 `580.178.04`，开源内核模块；无 vGPU，MIG 为 N/A。当前功耗上限 100 W，未更改。

使用 NVIDIA 官方同版本源码头文件编译独立 C 程序，经 `/dev/nvidiactl` 发起 GET 查询；仅创建并释放本进程的 RM 查询对象，没有硬件寄存器写入、SET 控制或驱动替换。

| 接口 | 命令号 | 本机结果 / 用途 |
|---|---|---|
| GR_GET_INFO | 0x20801201 | 满配容量 6 GPC、每 GPC 6 TPC、每 TPC 2 SM |
| GR_GET_GPC_MASK | 0x2080122a | 0x2f：物理 0、1、2、3、5 启用 |
| GR_GET_TPC_MASK | 0x2080122b | 每个物理 GPC 的掩码；非 MIG 路径明确按物理 GPC 查询 |
| GR_GET_SM_TO_GPC_TPC_MAPPINGS | 0x2080120f | 56 条 SM 映射 |
| GR_GET_GLOBAL_SM_ORDER | 0x2080121b | 56 SM / 28 TPC，完整逻辑顺序 |
| GRMGR_GET_GR_FS_INFO | 0x20803801 | 5 个 GPC、逻辑→物理映射及独立的 TPC 掩码交叉检查 |
| GR_GET_PHYS_GPC_MASK | 0x20801232 | 0x1b，权限不足；其返回掩码无效，未用于任何结论 |

最初的探索查询保留在 `topology_0.*`。增加逻辑→物理映射接口后，`topology_1.json`、`topology_2.json`、`topology_3.json` 三个独立进程的结果完全相同。所有用于结论的接口及其子查询返回 0。CUDA 驱动 API 另外读取到 56 SM、计算能力 7.5，与掩码计数和 56 条逐 SM 映射一致。

核验还包括：每个逻辑 TPC 恰有 SM 0、1 两条；所有 GPC 逐项计数与物理掩码一致；两个 SM 映射接口逐条一致；有效物理 GPC 集合与 GPC 掩码一致。完整检查见 [AUDIT.json](/home/ubuntu/文档/ChatGPT/numa_gpu/gpc-mask-t10/reports/AUDIT.json)，原始读取见 [topology_1.json](/home/ubuntu/文档/ChatGPT/numa_gpu/gpc-mask-t10/evidence/topology_1.json)。

`GR_GET_INFO` 的历史 `SHADER_PIPE_COUNT/SUB_COUNT` 字段实际返回 5/28，其旧注释容易混淆。本次没有按旧注释解释为 5 TPC/28 SM；总数采用明确的 `numSm/numTpc`、掩码和 CUDA 属性交叉确认。

## 对已有优化的具体意义

**“这张卡每个 GPC 均匀裁剪，因此缺乏结构差异”这一担忧不符合本机实读配置。** 但不均匀屏蔽只确定了资源分布，不证明同组访存必然更快，也不证明关闭 GPC 会改变有效路由长度。即使均匀屏蔽，同 TPC、同 GPC 与跨 GPC 的访问代价仍需要实验判断；均匀与否不能单独决定论文价值。

本次还将既有冻结配对表与硬件分组做了纯 CPU 对照，没有重测或改写旧性能结果：

- 旧 `IDENTITY` 的 `(0,1)、(2,3)、…、(54,55)` **28 对全部是同 TPC**，也全部同 GPC。原固定基线已经具有局部分组特征。
- 既有页 17 的 `MINIMAX` 是 **5 对同 TPC、1 对同 GPC 不同 TPC、22 对跨 GPC**。这不能直接解释其快慢，尤其先前矩阵测的是经全局地址邮箱的完整往返，并非 SM 间裸连线距离。
- 不能据此把先前条件性收益改写为已证实的物理 NUMA 加速。此前正负结果、没有获得稳定净收益的结论保持。

接下来最有信息量的是固定地址与提交节奏，分层比较**同 TPC、同 GPC 不同 TPC、跨 GPC**，并在相同负载与并发下检查实际延迟；同时对照 10-SM 与 12-SM GPC 的竞争差异。只有层级代价稳定且算子关键路径受其影响，才值得加入调度。可先用本次静态映射在 CPU 上编译常量调度，避免每次 kernel 动态查表/抢任务。本次仅完成分布检查，没有启动新的性能实验。

## 重现与来源

查询源程序：[read_topology.c](/home/ubuntu/文档/ChatGPT/numa_gpu/gpc-mask-t10/src/read_topology.c)。构建：在工作区执行 `bash gpc-mask-t10/src/build.sh`；读取：`gpc-mask-t10/read_topology > /tmp/t10-topology.json 2> /tmp/t10-topology.log`。当前账号即可完成用于结论的所有查询，不需要 sudo。该程序限定单 GPU 环境，头文件对应 580.178.04；其他驱动版本须重新核对 ABI。

纯 CPU 复核及作图：`/home/ubuntu/projects/leetgpu-lab/.venv/bin/python3 gpc-mask-t10/src/audit_topology.py`。该脚本使用已保存数据，不访问 GPU。

- [NVIDIA 580.178.04 GR 控制接口](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/580.178.04/src/common/sdk/nvidia/inc/ctrl/ctrl2080/ctrl2080gr.h)：掩码、SM 映射与逻辑编号语义。
- [NVIDIA GR 查询实现](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/580.178.04/src/nvidia/src/kernel/gpu/gr/kernel_graphics.c)：`subdeviceCtrlCmdKGrGetTpcMask_IMPL` 注明非 MIG 时 GPC ID 为物理编号。
- [NVIDIA floorsweeping 映射接口](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/580.178.04/src/common/sdk/nvidia/inc/ctrl/ctrl2080/ctrl2080grmgr.h)：逻辑 GPC → chiplet/物理 GPC 与物理 TPC 掩码。
- [NVIDIA Turing 架构白皮书](https://www.nvidia.com/content/dam/en-zz/Solutions/design-visualization/technologies/turing-architecture/NVIDIA-Turing-Architecture-Whitepaper.pdf)：完整 TU102 72 SM、6 GPC，每 GPC 6 TPC、每 TPC 2 SM。
- [NVIDIA PTX `%smid` 定义](https://docs.nvidia.com/cuda/parallel-thread-execution/index.html#special-registers-smid)：SM 标识的适用范围与非坐标性质。

完整匹配版本源码压缩包保存在 `sources/`，SHA256 `f30d4c20feda9f570a69084573a72423067e1e2d46c50ca58c391664872a9e01`；来源和关键文件哈希见 `evidence/provenance.json`。
