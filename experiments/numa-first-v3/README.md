# NUMA-first V3：T10 实测工程

输入为用户指定的 `NUMA_FIRST_COMPILED_CAMPAIGN_20261016_V3.zip`；当前状态见 `STATUS.md`，运行目录见 `CURRENT_RUN.txt`。这是独立于旧 Q1 实验的新账本。所有 GPU 工作通过 `environment/gpu_worker.lock` 串行，24 GPU-worker 小时为上限。

本轮不联网、不安装、不更改驱动，不关闭保护。本机保持已有的 100 W 功耗上限；功耗上限不等于实际功率或锁定频率。数据与依赖均来自本机已有文件。

## 证据层次

1. `P1_PROTOCOL.json` 与 `derived/P1_SUMMARY.json`：原先冻结的 6 次主分配、96 strata。源 cubin 与记录保留。
2. `derived/P1_EXCEPTION_AUDIT.json`：逐 SM 的小工作集例外，包含所有条件。不能用大组平均值掩盖组内信号。
3. `FINE_REFINEMENT_FREEZE.json`：观察例外后单独开展的 P3 补充诊断。公开 2-SM 组标定，再实际合并为两个等量组验证；没有按 SM ID 忙等。
4. `FINE_SHIFT_FREEZE.json`：去除地址通用除法的等价补充编译。原数据不替换；新分配独立标记，不能冒充原先确认集。
5. `WORKLOAD_FREEZE.json`、`NATIVE_REPEAT_FREEZE.json`：三族原生工作负载与开发阶段确定的正式重复数。普通 Q1 对照不叫 NUMA 方法。
6. `ledger.jsonl`、各 worker 的 manifest / telemetry / output：失败和重试保留，只有完整成功块进入主估计。

## 可复算与边界

分析脚本在 `src/`。`analyze_probe.py` 从原始 CTA 二进制重算，`analyze_fine.py` 重算补充控制，`analyze_native.py` 从每请求记录重算块平均与探索性区间。统计独立单位为分配/进程块，不是 CTA 或帧数。

完整 GPU 复现依赖本机已有模型、CUDA/PyTorch/CUTLASS 与 Graphdeco 源码。最终小型审阅包提供聚合层复算资料和证据索引，不冒称携带完整模型及运行环境。所有未知 home、缺失硬件 counter、未支持策略及协议偏离均必须在最终报告单列。

## 最终配置与历史草案

- 编译 micro 的八策略以 `COMPILED_MICRO_FREEZE.json` 为准，正式执行顺序再由 `MICRO_ORDER_AMENDMENT.json` 修正为参考 Williams 顺序。修正在任何正式 phase 开始之前；GPU cubin、重复次数和全部数学操作未改，重新通过资格。
- `COMPILED_MICRO_FREEZE_INITIAL_ALIAS_ASSUMPTION.json` 是未执行的早期定义草案。最终 T 保持原数据，仅用同信息调整任务分配，和 M 独立测量；两者在均匀归约中的物理地址集合相同，不据此制造新颖性。
- `B_STAR_FREEZE.json` 在正式 phase 开始前，用唯一开发块选定 B/T 参照，并保留其完整数据快照。B* 只是已有策略的标签，不是新的样本。
- 实际生命周期为 `micro_lifecycle.cpp` / `compiled_lifecycle_job.py`：真实释放、重申请和扩容，测试合成消费者 N/T/M。早先准备的 `lifecycle_native.py` / `lifecycle_job.py` 没有执行，不算真实应用生命周期结果。
- 是否执行以新账本 `ledger.jsonl`、实际 command 和原始输出为准。输入包的参考测试、规划矩阵、草案文件、仅 REQUESTED 后归档的请求都不算 GPU 结果。
- `compiled/micro/SASS_SOURCE_AUDIT.json` 解释 slot 序言开销；冻结文档“per-CTA once”指 CTA 不变的循环外表达式，不是整个 CTA 只有一次硬件指令执行。原生 tile 页统计也只是候选颜色起始地址的结构代理，非精确消费页或物理 home。
