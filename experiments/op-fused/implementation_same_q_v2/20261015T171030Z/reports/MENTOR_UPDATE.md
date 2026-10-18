# 导师更新：T10 同 q 与主体复核

这次补齐了上一轮最重要的缺失对照：把相同 q=1 的 FULL、普通 CACHE 和精简 visitor 放在同一数学体与 worker 序列下比较。

- 新确认：精简 q1 / CACHEq1 **0.9977 [0.9964, 0.9991]**；FULLq1 / CACHEq1 **1.0062 [1.0049, 1.0076]**。
- 精简 q1 / LIB：旧回归 **1.6872 [1.6362, 1.7696]**，新确认 **1.3682 [1.3630, 1.3741]**；完整层 CPU-ready **1.3537 [1.2464, 1.4219]**。
- 全局配方 r0、固定 q=1；主体适配与遍历/实现开销单列，不能把它们叫自适应信息增益。
- 合法 activation 融合平均节约约 0.4%–0.7% 层时间；8 槽输入变化下，候选相对同融合 LIB 仍约慢 41%。这属于小幅工程收益，未解决主体差距。
- 数值摘要失败 0；新增 GPU-worker 0.894 小时，累计 6.363/16 小时。

结论范围：`METHOD_EVIDENCE_UNRESOLVED / NO_NEW_ADAPTIVE_INFORMATION_IMPLEMENTED / BACKBONE_GAP_REMAINS / Q1_IMPLEMENTATION_OVERHEAD_FOUND`。以上区间为探索性 95% 按进程块区间，六块数据不是论文充分性保证。静态描述符、热权重、合成 post-route 是已测范围；在线动态路由、真实模型与物理 NUMA 均未测。
