from pathlib import Path
import json,sys
R=Path(__file__).resolve().parents[1]
c=json.loads((R/'campaign.json').read_text()); cases=json.loads((R/'plans/cases.json').read_text())
assert sum(s['minutes'] for s in c['stages'])==510
assert c['wall_budget_minutes']==510 and c['wall_hard_stop_minutes']==540
assert c['gpu_worker_cap_minutes']<c['wall_budget_minutes']
assert len(c['actions'])==9 and sum(a['placement'] for a in c['actions'])==6
from collections import Counter
assert Counter(x['split'] for x in cases)=={'development':24,'confirmation':16,'regression':8,'ood_bypass':4}
assert len({x['id'] for x in cases})==52
assert len({(x['M'],x['N'],x['K']) for x in cases})==52
assert all(x['measured'] is False for x in cases)
dev=[x for x in cases if x['split']=='development']
bins=Counter((0 if x['M']<=8 else 1 if x['M']<=64 else 2,x['N']>4096) for x in dev)
assert len(bins)==6 and min(bins.values())>0
for x in cases:
    assert min(x['M'],x['N'],x['K'])>0
    assert 2*x['K']*(x['M']+x['N'])+4*x['M']*x['N']*8 < 4*1024**3
trace=json.loads((R/'plans/dispatch_traces.json').read_text())
assert len(trace['traces'])==3
ids={x['id'] for x in cases}
assert all(len(v)==128 and set(v)<=ids for v in trace['traces'].values())
counts=c['planned_counts']
assert counts['formal_action_main']==1296 and counts['formal_action_anchors']==288
assert counts['resource_card_cell_episodes']==256
assert counts['deployment_traces']==72 and counts['ffn_chain_phases']==96
print(json.dumps({'status':'CPU_PLAN_CHECK_PASS','shape_count':len(cases),'wall_minutes':510,'formal_action_phases_max':1584,'does_not_establish':'GPU correctness, device capability or performance'},ensure_ascii=False,indent=2))

orders=json.loads((R/"plans/formal_orders.json").read_text())["orders"]
assert len(orders)==144
assert len({(o["case_id"],o["block"]) for o in orders})==144
assert all(set(o["main_order"])==set(a["id"] for a in c["actions"]) for o in orders)
