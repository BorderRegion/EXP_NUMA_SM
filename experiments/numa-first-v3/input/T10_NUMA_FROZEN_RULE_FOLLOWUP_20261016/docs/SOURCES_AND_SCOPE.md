# 来源与本次新设计的边界

## 已提供资料事实

1. `NUMA_FIRST_V3_T10_REPORT.md`：粗28/28组主条件没有稳定正交互；fine分支在2MiB报告约0.979相关及约0.467的局部signed-log百分点；真实交换方向依运行状态而变。报告不是物理NUMA证明。
2. `CALIBRATION_RULE_AUDIT.md`：8个micro分配的2MiB规则为0x33/bias0，属region编号，原先每次重新标定。
3. 原包 `src/micro_consume.cu`、`fine_shift_runner.cpp`：原计时consumer有SM/clock/record写入；细标定grid=2且每region重复抽样，正式consumergrid=32/group。
4. 原包 `compact_raw/fine_shift_0/fits.csv`、`merged_2097152.csv`、`rosters.csv`：本包FROZEN_RULE的唯一分组来源，开发样本，未根据确认赢家挑选。复制的CSV保持原字节。
5. 用户已授权T10运行状态控制，要求本地离线、连续执行、先NUMA证据再应用，不使用新增任务查询表。

本包没有重跑GPU，不宣称重新验证全部旧统计。S0—S5、固定a/b任务位置、新反事实和DIAG-free骨架是**本次提出的实验设计**。

## 此次外部核对（仅提供给人类/本地资料留档，Codex无需联网）

- NVIDIA Green Contexts：分区计算资源不等于物理内存节点，独立work的并发推进不自动保证。
  https://docs.nvidia.com/cuda/cuda-programming-guide/04-special-topics/green-contexts.html
- NVIDIA nvidia-smi：power cap须在本机报告范围内；requested/enforced/actual draw不同，受权限和设备支持约束。
  https://docs.nvidia.com/deploy/nvidia-smi/index.html
- NVIDIA Nsight Compute Profiling Guide：默认replay/cache控制和序列化可能改变原程序行为，不能把profile时间当正式计时。
  https://docs.nvidia.com/nsight-compute/ProfilingGuide/index.html

引用只支持对应接口/计量边界，不为0x33赋予物理意义，也不表示本机安装的版本拥有在线文档全部能力。

## 不授权的扩展

不重新读完全部论文才开始；不扩大到5070Ti；不扩模型/渲染/稀疏；不重新做全地址hash逆向；不更换driver/固件/私有mask；不关闭保护；不从负结果转到q1调度或检查器项目。

本轮是机制诊断，不是新系统开发。即使得到正收益，也只能按实际micro、资源组和访问条件报告，不能直接写真实应用加速或论文成立。
