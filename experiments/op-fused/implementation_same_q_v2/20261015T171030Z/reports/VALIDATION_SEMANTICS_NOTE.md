# 位级检查口径补充

源审查发现复用的算子 harness 用 torch.equal(FP16, FP16) 命名 same_body_bitwise。它验证数值完全相等，但不区分 +0/-0，因此本轮原始字段不应称为逐 phase 的原始位比较。既有日志不回写，计时与冻结不改。

在正式计时结束后添加一次有限资格 worker：固定 grouped-003、grouped-057，复用各六块的实际 payload seed，在 CORE/CACHEq1/FULLq1/Q1_MINIMAL 上比较完整 int16 视图。它只补足每块少量原始位样本，不形成新性能观测，也不替换任何正式结果。层和融合资格已使用 int16 视图。

此补充不放宽容差、不改变数学路径、不因输赢选择样例。算子 phase 原字段按“FP16 value equality”解释；附加资格结果单列。
