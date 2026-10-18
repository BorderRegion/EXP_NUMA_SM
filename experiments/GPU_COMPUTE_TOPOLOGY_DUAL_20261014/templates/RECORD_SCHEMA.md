# 实际记录字段约定

以下是字段合同，不是已测数据。null表示unknown；数值0只用于真的测得/统计到零。

## manifest.json（每进程）
`schema_version, run_id, parent_run_id, platform, device_alias, campaign_id, stage, status, protocol_sha256, method_source_sha256, build_id, git_commit, git_dirty, diff_ref, environment_ref, capability_ref, inputs_manifest_sha256, strategy_order, calibration_split_id, test_split_id, plan_sha256, start_utc, end_utc, worker_seconds, actual_cost, cost_unit, output_index_ref, failure_reason`

## capacity_samples.csv
`run_id, kernel_family, input_size_id, logical_work_count, group_id, layout_id, actual_smid_set_ref, sm_count, cluster_size, cluster_qualified, concurrent_mode, round_id, isolated_or_concurrent, cpu_ready_ms, gpu_event_ms, tasks_per_ms, register_decl, shared_decl, occupancy_api_value, compiled_recipe_id, diagnostics_enabled, output_status`

## frames.csv
`run_id, workload_id, input_id, sequence_id, block_id, phase_id, policy, frame_id, camera_or_request_id, plan_generation, cpu_ready_ms, gpu_pipeline_ms, upstream_ms, render_or_operator_ms, additional_setup_ms, planner_calls, plan_D2H_bytes, plan_H2D_bytes, recompile_count, logical_task_count, fallback_count, device_memory_bytes, output_screen_status`

## topology.csv
`run_id, process_id, launch_id, cluster_id, block_rank, cluster_size, cluster_semantics_qualified, sm_begin, sm_end, group_id, output_status, provenance_level`

## paired_blocks.json（stats工具输入）
每项：`platform, condition, block_id, reference_ms, candidate_ms`。必须先按一个完整合法进程块聚合，不能每帧塞一项伪装独立块。主对照分别输出M/N与M/R，禁止合并不同reference。

## init_costs.jsonl
`run_id, device_profile_ms, workload_profile_ms, scene_map_ms, compilation_ms, plan_upload_ms, resource_setup_ms, deployment_extra_isolated, source_reused, generation_event, timestamp_utc`
如果无法隔离deployment-only cost，`deployment_extra_isolated=false`，不要报告精确break-even。

## plan_card.json
`generation, valid_device_alias, valid_kernel_hash, valid_input_contract, data_layout_id, calibrated_group_ids, task_type_rule, weights_source, rate_table_ref, concurrent_calibration_ref, group_eligibility, logical_task_map_ref, exactly_once_proof_ref, expected_online_costs, fallback_rule, invalidation_events`
不以默认true代替证据；合法性可以由构造保证，但须注明范围和来源。
