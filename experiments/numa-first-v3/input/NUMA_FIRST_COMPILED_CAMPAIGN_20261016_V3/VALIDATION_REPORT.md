# 交付前检查

本次只检查任务包与CPU辅助数学，没有执行GPU、NUMA检测、硬件设置、CUDA编译或应用实验。

- 22项CPU单元测试通过，涉及有限布局全覆盖/逆映射、地址合法域、2×2交互、无收益不可摊销、8策略平衡顺序、预算与计划数量。
- 对1–8个地址bit的所有非零mask与两种bias枚举了二域布局；这是数学双射检查，不是物理地址模型验证。
- 合同禁止运行时调度LUT和新增小调度kernel；辅助检查只是核对配置，实际实施仍需source/SASS与执行证据。
- Python语法、JSON、阶段预算与矩阵核对通过。T10/5070Ti各24 worker小时；应用主1536策略session，另有384次首尾锚测量。
- 文献依据与本轮设计假设分列，未提供或复制任何真实GPU的地址hash。
- 包内无自动执行nvidia-smi写操作或联网命令的脚本；功耗控制为明确授权后的本机实施任务。

## 单元测试实际输出

```text
test_affine_covers_full_set (test_reference.LayoutTests.test_affine_covers_full_set) ... ok
test_all_small_layouts_bijective (test_reference.LayoutTests.test_all_small_layouts_bijective) ... ok
test_byte_offsets_preserve_intra_granule (test_reference.LayoutTests.test_byte_offsets_preserve_intra_granule) ... ok
test_generated_source_has_no_task_lookup (test_reference.LayoutTests.test_generated_source_has_no_task_lookup) ... ok
test_inverse_and_color (test_reference.LayoutTests.test_inverse_and_color) ... ok
test_non_coprime_rejected (test_reference.LayoutTests.test_non_coprime_rejected) ... ok
test_out_of_range_rejected (test_reference.LayoutTests.test_out_of_range_rejected) ... ok
test_budget (test_reference.PlanTests.test_budget) ... ok
test_cap_is_disclosed (test_reference.PlanTests.test_cap_is_disclosed) ... ok
test_no_table_contract (test_reference.PlanTests.test_no_table_contract) ... ok
test_power_authority_distinct (test_reference.PlanTests.test_power_authority_distinct) ... ok
test_primary_counts_and_anchors (test_reference.PlanTests.test_primary_counts_and_anchors) ... ok
test_task_plan_is_not_results (test_reference.PlanTests.test_task_plan_is_not_results) ... ok
test_bad_times_rejected (test_reference.StatTests.test_bad_times_rejected) ... ok
test_break_even (test_reference.StatTests.test_break_even) ... ok
test_geomean (test_reference.StatTests.test_geomean) ... ok
test_interaction_detects_cross_term (test_reference.StatTests.test_interaction_detects_cross_term) ... ok
test_interaction_zero_for_row_column_only (test_reference.StatTests.test_interaction_zero_for_row_column_only) ... ok
test_no_amortization_for_slow_candidate (test_reference.StatTests.test_no_amortization_for_slow_candidate) ... ok
test_non_finite_rejected (test_reference.StatTests.test_non_finite_rejected) ... ok
test_williams_pair_balance (test_reference.StatTests.test_williams_pair_balance) ... ok
test_williams_position_balance (test_reference.StatTests.test_williams_position_balance) ... ok

----------------------------------------------------------------------
Ran 22 tests in 0.113s

OK
```
