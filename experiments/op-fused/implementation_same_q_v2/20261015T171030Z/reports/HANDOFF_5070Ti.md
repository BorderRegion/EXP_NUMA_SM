# 5070Ti 交接

可直接带走：同 q 三版本的代数合同与独立 Q1_MINIMAL；所有旧结构标记已见；新开发/确认分离；固定同体 worker；普通单 GEMM vs grouped count=1 分解；FP64 与显式 half 物化边界；完整层、相同融合等级和 activation-ring 对照；所有正负结果与失败记录。

必须在新实机重新确认：设备 compute capability、驱动/runtime/成熟库与 CUTLASS 支持、合法高效数学实例、实际寄存器/shared/occupancy、worker 规则、功耗/频率制度与显存余量。不要照抄 T10 SM75 配方，也不要将 100W 当跨卡公平性充分条件。

先建立强数学主体，然后冻结同 q 简单基线。新变体只能按新开发数据选型，当前确认点已见，不能继续称盲测。保留 CORE、CACHEq1、FULLq1、Q1_MINIMAL 的相同 logical tile/worker 顺序证据。若现有自适应规则仍 q1，必须报告机制不活跃，不调大预算救正例。

不可迁移的主张：缓存命中因果、DRAM/spill根因、物理 SM 亲和/NUMA、动态 router 或跨模型泛化。T10 本轮没有相应干预/counter/模型证据。

当前轮到此收尾；该交接是复现实验约束，不是在另一主机启动新实验的授权或已经完成的结果。
