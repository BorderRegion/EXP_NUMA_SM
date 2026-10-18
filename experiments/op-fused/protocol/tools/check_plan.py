"""Offline consistency check for the supplied design; not GPU qualification."""
from pathlib import Path
import json
from collections import Counter
from make_matrix import build_matrix


def check():
    root=Path(__file__).resolve().parents[1]
    cfg=json.loads((root/'configs/campaign.json').read_text())
    errors=[]
    for name,p in cfg['platforms'].items():
        if abs(sum(p['stage_hours'].values())-p['worker_hours'])>1e-9:
            errors.append(f'{name}: stage budget mismatch')
    if sum(p['worker_hours'] for p in cfg['platforms'].values())!=40:
        errors.append('combined budget not 40h')
    if not cfg['execution']['offline'] or cfg['execution']['new_paid_resources_authorized']:
        errors.append('execution scope differs')
    rows=build_matrix()
    cnt=Counter((r['suite'],r['split']) for r in rows)
    expected={('grouped','calibration'):24,('grouped','test'):72,
              ('attention_decode','calibration'):16,('attention_decode','test'):32,
              ('moe_layer','calibration'):6,('moe_layer','test'):18,
              ('dense_control','calibration'):12,('dense_control','test'):12,
              ('heterogeneous_k','calibration'):6,('heterogeneous_k','test'):6,
              ('prefill_control','calibration'):4,('prefill_control','test'):8}
    if dict(cnt)!=expected:errors.append('matrix split mismatch')
    if len(rows)!=216 or len({r['case_id'] for r in rows})!=216:errors.append('plan ID mismatch')
    for r in rows:
        if r['suite']=='grouped' and sum(r['rows_per_expert'])!=r['total_routed_rows']:
            errors.append(f"{r['case_id']}: routed count mismatch")
        if r['suite']=='attention_decode' and sum(r['lengths'])!=r['batch']*r['mean_kv']:
            errors.append(f"{r['case_id']}: length mismatch")
    f=cfg['formal']; b=f['independent_blocks']; a=f['anchor_phases']
    for suite,key,policy in [('grouped','max_grouped_phases','grouped_policy_phases'),
                             ('attention_decode','max_attention_phases','attention_policy_phases'),
                             ('moe_layer','max_layer_phases','layer_policy_phases')]:
        if cnt[suite,'test']*b*(f[policy]+a)!=f[key]:errors.append(f'{key}: count mismatch')
    if cfg['candidate']['max_configs'] != len(cfg['candidate']['q_cap'])*len(cfg['candidate']['target_waves'])*cfg['candidate']['math_tile_recipes_max']:
        errors.append('candidate tuning budget mismatch')
    return {'status':'PASS' if not errors else 'FAIL','errors':errors,'plans':len(rows),
            'plan_counts':{f'{k[0]}/{k[1]}':v for k,v in cnt.items()},
            'warning':'CPU design check only. No GPU or backend was accessed.'}
if __name__=='__main__':
    result=check();print(json.dumps(result,ensure_ascii=False,indent=2))
    raise SystemExit(bool(result['errors']))
