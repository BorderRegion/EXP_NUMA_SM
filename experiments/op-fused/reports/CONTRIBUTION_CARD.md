# 贡献卡

待证命题：成熟算子内有界复用包和尾部约束能否超出同融合、同Graph普通调度？

本轮答案：尚未检验；FULL没有合格GPU实现。

最近方法：包内S1 CUTLASS grouped scheduler、S2 persistent cache-aware grouped GEMM、S4 FlashInfer；本轮离线未全文查新。

实际新增：可复核T10原生基线、decode GQA布局适配与准备成本、动态合成输入/KV ring、温控功耗策略记录、方案退化区间审查。

不能主张：新调度算法优于库、物理NUMA亲和、固定功耗硬件结论、完整模型收益、跨GPU泛化。

下一步所需：完整本地可修改SM75 Tensor Core主体及依赖、同融合强基线、当前GPU动态metadata接入、合格FP16模型合同与独立真实trace。
