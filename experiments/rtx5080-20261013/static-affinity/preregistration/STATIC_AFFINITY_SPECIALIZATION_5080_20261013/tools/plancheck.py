"""Offline plan consistency checker, NOT a GPU harness."""
from __future__ import annotations
import json
from pathlib import Path
import sys


def validate(plan: dict) -> dict:
    permissions = plan['permissions']
    if any(value is not False for value in permissions.values()):
        raise ValueError('This plan does not authorize external/system actions')
    budgets = plan['budget_worker_hours']
    if set(budgets) != {f'E{i}' for i in range(8)} | {'reserve'}:
        raise ValueError('Stage budget keys differ from the frozen design')
    if any(type(v) not in (int, float) or v < 0 for v in budgets.values()):
        raise ValueError('Invalid stage budget')
    if abs(sum(budgets.values()) - plan['worker_hours_cap']) > 1e-9:
        raise ValueError('Stage budget sum differs from cap')
    if plan['worker_hours_cap'] > 24:
        raise ValueError('Exceeds authorized new campaign cap')
    policies = plan['policies']
    if len(policies) != 8 or len(set(policies)) != 8:
        raise ValueError('Expected eight unique policies')
    m=plan['dynamic_matrix']; s=plan['snapshot_matrix']; f=plan['mechanism_matrix']
    dyn=m['scenes']*m['tracks_per_scene']*m['independent_blocks']*(m['policy_count']+m['extra_native_anchor'])
    snap=s['scenes']*s['snapshots_per_scene']*s['policy_count']*s['independent_blocks']
    fixed=f['working_sets']*f['access_profiles']*f['policies']*f['independent_blocks']
    for actual, configured, label in ((dyn,m['sessions_cap'],'dynamic'),(snap,s['sessions_cap'],'snapshot'),(fixed,f['sessions_cap'],'fixed mechanism')):
        if actual != configured:
            raise ValueError(f'{label} matrix mismatch')
    h=plan['hardware_probe']
    strata=h['allocation_epochs']*len(h['working_set_l2_multipliers'])*len(h['load_recipes'])*len(h['concurrency_levels'])
    if strata != h['matrix_strata_cap']:
        raise ValueError('Affinity matrix strata mismatch')
    if h['development_epochs']+h['confirmation_epochs'] != h['allocation_epochs']:
        raise ValueError('Allocation split mismatch')
    if h['fit_regions']+h['heldout_regions'] != h['regions_per_stratum']:
        raise ValueError('Region split mismatch')
    if plan['candidate_limit']['static_joint_algorithm'] != 1:
        raise ValueError('Do not expand the candidate family')
    if not plan['safety']['no_busy_wait_for_sm'] or not plan['safety']['stop_on_device_health_event']:
        raise ValueError('Safety contract changed')
    return {'design_checked_only':True, 'gpu_experiments_executed':False,
            'budget_worker_hours':sum(budgets.values()), 'affinity_strata_cap':strata,
            'fixed_mechanism_sessions_cap':fixed, 'snapshot_sessions_cap':snap,
            'dynamic_sessions_cap':dyn,'dynamic_measured_frames_cap':dyn*m['measured_frames'],
            'dynamic_blocks':m['scenes']*m['tracks_per_scene']*m['independent_blocks'],
            'notes':'Conditional branches are not cumulative obligations. No results are generated.'}

if __name__ == '__main__':
    if len(sys.argv)!=2:
        raise SystemExit('Usage: python tools/plancheck.py campaign.json')
    print(json.dumps(validate(json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))),ensure_ascii=False,indent=2))
