from pathlib import Path
import json,collections
root=Path(__file__).resolve().parents[1]
def read(p):return json.loads((root/p).read_text())
c=read('campaign.json');cases=read('plans/cases.json');pairs=read('plans/pair_orders.json');tr=read('plans/traces.json')['signatures'];ffn=read('plans/ffn.json');ids={x['id']:x for x in cases}
assert sum(s['wall_minutes'] for s in c['stages'])==510
assert sum(s['gpu_minutes'] for s in c['stages'])==240
assert 240 <= 330-70.17
assert len(cases)==52 and len(ids)==52
assert len({(x['M'],x['N'],x['K']) for x in cases})==52
cnt=collections.Counter(p['stage'] for p in pairs)
assert cnt=={'CALIBRATION':1152,'EVALUATION':2304,'PC_DIRECT':144},cnt
assert len({p['id'] for p in pairs})==len(pairs)==3600
assert all(p['order'] in ('ABBA','BAAB') for p in pairs)
assert all(p['case_id'] in ids for p in pairs)
v={x['id'] for x in cases if x['cohort']=='new_confirmation'}
assert len(v)==16 and all(len(t)==128 and v <= set(t) for t in tr.values())
for f in ffn:
 x=ids[f['first_case']];assert (f['M'],f['intermediate'],f['hidden'])==(x['M'],x['N'],x['K'])
print(json.dumps(dict(status='CPU_PLAN_VALIDATED_NOT_GPU_RUN',shapes=len(cases),quartets=dict(cnt),main_windows=len(pairs)*4,wall_minutes=510,gpu_minutes=240,all_new_cases_in_every_trace=True),indent=2))
