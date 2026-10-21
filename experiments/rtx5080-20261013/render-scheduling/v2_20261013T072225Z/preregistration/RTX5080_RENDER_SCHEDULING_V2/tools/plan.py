#!/usr/bin/env python3
"""Offline CPU plan checks. No GPU, network, subprocess, or experiment execution."""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
from typing import Any


class PlanError(ValueError):
    """Invalid or unsafe campaign plan."""


def load_plan(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding='utf-8') as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise PlanError('The plan root must be a JSON object.')
    return value


def counts(plan: dict[str, Any], topology: bool) -> dict[str, int]:
    app, policies = plan['application'], plan['policies']
    n = len(policies['common']) + (len(policies['topology_extra']) if topology else 0)
    main = app['dev_scenes_max'] * app['test_trajectories_per_scene'] * n * app['full_blocks']
    hold = app['heldout_scenes_max'] * app['test_trajectories_per_scene'] * len(policies['extension_policies']) * app['full_blocks']
    secondary = app['dev_scenes_max'] * len(policies['extension_policies']) * app['secondary_blocks']
    negative = app['dev_scenes_max'] * app['test_trajectories_per_scene'] * len(policies['extension_policies']) * app['negative_blocks']
    micro = plan['micro']
    return {
        'main_policies': n, 'main_sessions': main, 'heldout_sessions': hold,
        'secondary_sessions': secondary, 'full_application_sessions': main + hold + secondary,
        'negative_application_sessions': negative,
        'micro_configurations': len(micro['working_set_l2_multipliers']) * micro['reuse_levels'] * micro['skew_levels'] * micro['schedule_modes'],
        'main_measured_frames_planned': main * app['measured_frames'],
    }


def validate(plan: dict[str, Any]) -> dict[str, Any]:
    auth = plan['authorization']
    for key in ('network', 'ssh', 'download', 'driver_change', 'rent_gpu', 'system_privilege_change'):
        if auth.get(key) is not False:
            raise PlanError(f'{key} must be explicitly false.')
    if auth.get('paid_budget') != 0:
        raise PlanError('This campaign has no additional paid authorization.')
    if auth.get('cache_load_branch_preapproved') is not True or auth.get('topology_required_for_cache_branch') is not False:
        raise PlanError('Do not block the preapproved cache/load branch on NUMA.')
    if plan.get('execution') != 'local_offline':
        raise PlanError('Execution must be local_offline.')
    ref = plan['expected_hardware_reference']
    if ref.get('measured') is not False or ref.get('physical_numa_domains') is not None:
        raise PlanError('Hardware reference cannot masquerade as a measured topology.')
    budget = plan['budget']
    stages = list(budget['stage_hours'].values())
    if not stages or any(not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v) or v < 0 for v in stages):
        raise PlanError('Stage budgets must be finite nonnegative numbers.')
    if not math.isclose(sum(stages), budget['gpu_worker_hours_total'], abs_tol=1e-9):
        raise PlanError('Stage budgets must sum to the total cap.')
    if budget['gpu_worker_hours_total'] > 12 or budget['gpu_workers'] != 1:
        raise PlanError('Single-worker / 12-hour limit exceeded.')
    if budget['topology_worker_minutes_cap'] > 45:
        raise PlanError('Topology probing must stay bounded.')
    if budget['application_headroom_gib_min'] < 2 or budget['application_headroom_total_fraction'] < 0.15:
        raise PlanError('Application memory headroom is too small.')
    if budget['outputs_soft_gib'] > budget['outputs_hard_gib']:
        raise PlanError('Storage limits are reversed.')
    app = plan['application']
    if app['new_candidate_algorithms_max'] != 1 or app['executor_forms_max'] > 2:
        raise PlanError('Scope changed: candidate / executor limit exceeded.')
    if app['warmup_frames_min'] < 256 or app['warmup_seconds_min'] < 2:
        raise PlanError('Warmup minimum was reduced.')
    if app['measured_frames'] != 512:
        raise PlanError('Measured length differs from the registered plan.')
    if plan['calibration']['test_data_tuning'] is not False:
        raise PlanError('Test data may not be used for tuning.')
    if plan['decision']['allow_more_algorithms_after_negative'] is not False:
        raise PlanError('A negative result does not authorize a new algorithm.')
    policies = plan['policies']['common'] + plan['policies']['topology_extra']
    if len(set(policies)) != len(policies):
        raise PlanError('Policy IDs must be unique.')
    if 'B0_NATIVE' not in policies or 'B5_GROUP_BALANCE' not in policies:
        raise PlanError('A strong baseline was removed.')
    result = {key: counts(plan, t) for key, t in (('A_topology', True), ('B_cache', False))}
    limits = plan['limits']
    for branch in result.values():
        for metric, cap in (
            ('main_sessions','main_sessions_max'),('heldout_sessions','heldout_sessions_max'),
            ('secondary_sessions','secondary_sessions_max'),('full_application_sessions','full_application_sessions_max'),
            ('negative_application_sessions','negative_application_sessions_max')):
            if branch[metric] > limits[cap]:
                raise PlanError(f'{metric} exceeds the registered cap.')
    return {'plan_valid': True, 'gpu_experiments_executed': False, 'counts': result,
            'worker_hours_cap': budget['gpu_worker_hours_total'],
            'reference_values_are_measurements': False}


def select_route(*, real_renderer_ready: bool, stable_interaction: bool | None,
                 legal_control: bool | None, useful_control_test: bool | None) -> str:
    """Select only a preapproved route; None is unknown, not measured false."""
    flags = (real_renderer_ready, stable_interaction, legal_control, useful_control_test)
    if any(v is not None and not isinstance(v, bool) for v in flags):
        raise PlanError('Evidence flags must be bool or None, never a free-form truthy value.')
    if real_renderer_ready is not True:
        return 'CPU_OR_MICRO_ONLY'
    if stable_interaction is True and legal_control is True and useful_control_test is True:
        return 'TOPOLOGY_PLUS_CACHE'
    return 'CACHE_AND_LOAD'


def validate_tile_permutation(ids: list[int], task_count: int) -> bool:
    """CPU structural check only; does not prove exactly-once GPU execution."""
    if not isinstance(task_count, int) or isinstance(task_count, bool) or task_count < 0:
        raise PlanError('task_count must be a nonnegative integer.')
    if len(ids) != task_count or any(not isinstance(i, int) or isinstance(i, bool) for i in ids):
        return False
    return set(ids) == set(range(task_count))


def time_reduction_pct(reference_ms: float, candidate_ms: float) -> float:
    """Positive means less time. This is not an FPS percentage."""
    if any(not math.isfinite(v) or v <= 0 for v in (reference_ms, candidate_ms)):
        raise PlanError('Durations must be finite and strictly positive.')
    return 100.0 * (1.0 - candidate_ms / reference_ms)


def break_even_frames(one_time_extra_ms: float, per_frame_saving_ms: float) -> int | None:
    """None means no finite break-even under the supplied constant-saving model."""
    if not math.isfinite(one_time_extra_ms) or not math.isfinite(per_frame_saving_ms) or one_time_extra_ms < 0:
        raise PlanError('Setup cost must be finite/nonnegative and saving finite.')
    if per_frame_saving_ms <= 0:
        return None
    return math.ceil(one_time_extra_ms / per_frame_saving_ms)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('check', 'summary'))
    parser.add_argument('plan', type=Path)
    args = parser.parse_args()
    try:
        answer = validate(load_plan(args.plan))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(2, f'PLAN ERROR: {exc}\n')
    print(json.dumps(answer, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
