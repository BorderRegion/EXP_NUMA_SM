"""Anchor choice and repeated input-family sensitivity, never favorable selection."""
import collections,json,math
import numpy as np
from analyze_native import ROOT,effect,dump
D=ROOT/'derived/native_v1';groups=collections.defaultdict(lambda:collections.defaultdict(list));durations=collections.defaultdict(list)
reg=[json.loads(x) for x in (ROOT/'registry/runs.jsonl').read_text().splitlines()]
for m in reg:
 if '_native_block_' in m['key']:cohort='native'
 elif '_strong_block_' in m['key']:cohort='strong'
 elif m['key'].startswith('E4_request_block_'):cohort='layer_request'
 else:continue
 for p in (ROOT/m['path']).glob('*.json'):
  x=json.loads(p.read_text())
  if 'case' not in x or 'phases' not in x:continue
  pp={y['variant']:y for y in x['phases'] if y['phase_role']=='primary'}
  aa={y['phase_role']:y for y in x['phases'] if y['phase_role'].startswith('anchor_')}
  if len(aa)!=2:continue
  anchor=aa['anchor_head']['variant']
  pairs=[('CUBLASLT_GRAPH','CUBLAS_GRAPH'),('CUBLAS_GRAPH','CUBLAS_EAGER'),('CUTLASS_READY','CUTLASS_RESIDENT'),('MATH_READY','CUTLASS_READY'),('CUTLASS_DYNAMIC16','CUTLASS_READY'),('CUBLAS_GRAPH_REQUEST','CUBLAS_EAGER_REQUEST'),('NATIVE_GROUPED_GRAPH','PER_EXPERT_GRAPH')]
  for y in x['phases']:durations[cohort].append(y['device_interval_ms']*y['measured_requests'])
  for a,b in pairs:
   if a not in pp or b not in pp:continue
   for endpoint,field in [('device','device_interval_ms'),('ready','operator_or_layer_ready_ms')]:
    g=groups[cohort,m['stage'],x['case']['case_id'],a+'/'+b,endpoint]
    g['primary'].append((x['block'],math.log(pp[a][field]/pp[b][field])))
    for role in ['anchor_head','anchor_tail']:
     av=aa[role][field] if a==anchor else pp[a][field];bv=aa[role][field] if b==anchor else pp[b][field]
     g[role].append((x['block'],math.log(av/bv)))
rows=[]
for (cohort,stage,ident,pair,ep),vals in sorted(groups.items()):
 effects={k:effect([v for b,v in vv]) for k,vv in vals.items()};ratios=[v['ratio'] for v in effects.values()]
 families=collections.defaultdict(list)
 for b,v in vals['primary']:families[b%3].append(v)
 familymeans=[float(np.mean(v)) for k,v in sorted(families.items())]
 rows.append(dict(cohort=cohort,stage=stage,case_id=ident,comparison=pair,endpoint=ep,anchor_effects=effects,anchor_direction_flip=min(ratios)<1<max(ratios),interpretation='DRIFT_LIMITED' if min(ratios)<1<max(ratios) else 'NO_ANCHOR_DIRECTION_FLIP_OBSERVED',three_seed_family_means=dict(zip(map(str,sorted(families)),map(math.exp,familymeans))),family_level_descriptive_range=[math.exp(min(familymeans)),math.exp(max(familymeans))],family_note='Three input seeds reused. Family means average their process blocks; range only, no new significance claim.'))
dump(D/'anchor_and_input_sensitivity.json',rows)
summary=dict(comparisons=len(rows),anchor_direction_flips=sum(x['anchor_direction_flip'] for x in rows),flips_by_cohort=dict(collections.Counter(x['cohort'] for x in rows if x['anchor_direction_flip'])),timing_windows={k:dict(phases=len(v),under_50ms=sum(x<50 for x in v),within_50_200ms=sum(50<=x<=200 for x in v),over_200ms=sum(x>200 for x in v),min_ms=min(v),max_ms=max(v)) for k,v in durations.items()},note='Direction flips near1 are sensitivity flags, not evidence of an algorithm effect. Original primary estimates remain primary. All request durations here sum measured device spans; they are not one uninterrupted batch.')
dump(D/'sensitivity_summary.json',summary);print(json.dumps(summary,indent=2))
