# 实验记录的最小字段

`run_id, platform, campaign_id, method_commit, backend, build_hash, case_id, origin, split, block_id, phase_id, phase_role, strategy, fusion_level, measurement_scope, math_config_hash, input_hash, route_or_length_hash, plan_generation, graph_mode, warmup_repeats, measured_repeats, elapsed_ms, cpu_ready_ms, gpu_interval_ms, status, validation_ref, source_ref, raw_ref`

`phase_role`只允许 primary / anchor / calibration / diagnostic。原始时间序列用二进制或CSV，一次落盘。
`status`只允许 PLANNED / RUNNING / COMPLETED / FAILED / NOT_QUALIFIED / UNSUPPORTED / MISSING_RESOURCE / BUDGET_SKIPPED / ABORTED。
没有time填null，不填0；FAILED不删行。主分析仅COMPLETED且资格有效的完整配对，其他行进入排除/缺项表。

额外资源字段：allocated/reserved/process_device_memory各自列；不要相加冒充峰值。sm_ids/counters只在实际采集时记录，缺失null。

账本：scheduler_kernel_nodes、total_kernel_nodes、memset_nodes、host_wait_count、plan_calls、metadata_D2H/H2D_bytes、metadata_device_bytes、plan_init_ms、compile_ms、graph_capture_ms；来源级别同时记录。
