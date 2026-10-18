# 同 q 等价与成本卡

给定 problem 的 gm×gn 网格、问题前缀与共同 worker 数 W，每个 worker 处理全局序号 b、b+W、b+2W……。空 expert 的 tile 数为零。

| 版本 | problem 顺序 | ordinal r 的 (m,n) | worker 步长 | 额外总量 / packet 状态 |
|---|---|---|---|---|
| CORE_ORIGINAL | 原输入顺序 | (r//gn,r%gn) | W | 无 |
| CACHE_Q1_LEGACY | 原输入顺序 | (r%gm,r//gm) | W | 不读取总量；保留通用 q/packet 状态 |
| FULL_Q1_LEGACY | 原输入顺序 | (r%gm,r//gm) | W | 每 CTA 内 warp 计算总 tile；保留 waves/K-budget 查询 |
| Q1_MINIMAL | 原输入顺序 | (r%gm,r//gm) | W | 无额外字段、总量规约、K-budget 或 sideband |
| CACHE_FIXED_BEST | 原输入顺序 | 冻结 q 的 N-panel packets | packet 序号步长 W | q 来自开发集，无新自适应信息 |

FULL/CACHE 的 qcap=1 时所有约束都返回 1。因此三个 q1 版本的问题、tile、worker 归属与访问次序一致；它们编译生成的寄存器和指令可以不同。Q1_MINIMAL 继承原生 CUTLASS visitor 的问题发现、前缀与 advance，只重写 threadblock_idx；没有单独 planner，也没有外部任务表。

CPU 小域 1,296 个配置证明直接枚举与旧 packet 参考在 q1 下序列相同，包含空 expert、尾块、四种 BM/BN 与不同 worker 数。GPU count_visits 验证恰好一次覆盖；完整输出按同数学体精确数值核对，原始位样本另列，见 VALIDATION_SEMANTICS_NOTE.md。它们不证明物理 SM 亲和或缓存命中因果。

所有版本在每个数学配方上使用四种 grouped visitor 中最小 occupancy 上限得到的共同 W。BN=64 的 host tile 总数、覆盖前缀、packet 统计、sideband 都读取真实 BN；没有继续使用 128 作为 N tile 宽度。work_budget=128 K tiles 的算法常量保留原值，与 BN 无关。
