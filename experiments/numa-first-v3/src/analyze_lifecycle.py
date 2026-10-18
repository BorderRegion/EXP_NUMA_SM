"""Actual free/reallocate/grow events, same-context N/T/M, saved-output audit."""
import csv,json,math
from collections import defaultdict
import numpy as np
from common import *
from analyze_probe import DT
r=runroot();led=[json.loads(x) for x in (r/'ledger.jsonl').read_text().splitlines()];rows=[];events=[];checks=0
for w in led:
 if not w['key'].startswith('compiled_lifecycle_') or w['status']!='COMPLETED':continue
 qual=w['key'].endswith('qualification');block=-1 if qual else int(w['key'].split('_b')[-1]);root=Path(w['out']);previous=0
 for event in range(3):
  p=root/f'event_{event}';ident=json.loads((p/'allocation.json').read_text());assert ident['event']==event and ident['capacity_bytes']==[2097152,2097152,8388608][event] and ident['previous_base']==previous and ident['previous_graphs_destroyed_and_buffer_freed'] and not ident['old_rule_used'];previous=ident['base'];size=ident['capacity_bytes'];expect=np.array([int(x['sum_onepass']) for x in csv.DictReader((p/f'expected_{size}.csv').open())],dtype=np.uint64);output=np.fromfile(p/'logical_outputs.bin','<u8');diag=np.fromfile(p/'diagnostic_outputs.bin',DT);cr=list(csv.DictReader((p/'checks.csv').open()));assert len(output)==len(diag)==len(cr)*64;f=list(csv.DictReader((p/'fits.csv').open()))[0];mask,bias=int(f['mask']),int(f['bias']);member=list(csv.DictReader((p/'membership.csv').open()));gids=sorted({int(x['group']) for x in member if x['kind']=='LEARNED'});sets=[{int(x['actual_sm']) for x in member if int(x['group'])==g} for g in gids];assert len(sets)==2 and len(sets[0])==len(sets[1])==28
  for c in cr:
   off=int(c['raw_u64_offset']);d=diag[off:off+64];assert np.array_equal(output[off:off+64],expect) and np.array_equal(d['sum'],expect) and np.array_equal(d['sm_begin'],d['sm_end']);method=c['policy']
   if method!='N':
    for j in range(64):
     domain=((j&mask).bit_count()%2)^bias if method=='T' else j//32;assert int(d['sm_begin'][j]) in sets[domain]
   checks+=1
  eventrow=dict(qualification=qual,block=block,event=event,identity=ident,fit=f,layout=json.loads((p/f'layout_cost_{size}.json').read_text()),common_context_setup=json.loads((p/'setup_costs.json').read_text()),source=str(p.relative_to(r)));events.append(eventrow);sample=defaultdict(list)
  for x in csv.DictReader((p/'samples.csv').open()):sample[x['policy'],x['role']].append(x)
  for q in csv.DictReader((p/'phases.csv').open()):
   z=sample[q['policy'],q['role']];assert len(z)==(8 if qual else 128);rows.append(dict(qualification=qual,block=block,event=event,policy=q['policy'],role=q['role'],ready_ms=float(np.mean([float(x['cpu_ready_ms']) for x in z])),event_ms=float(np.mean([float(x['event_ms']) for x in z])),batch_ms=float(q['batch_event_ms'])/int(q['batch_repeats']),graph_build_ms=float(q['graph_build_ms']),layout_copy_ms=float(q['layout_copy_ms']),requests=len(z)))
def ci(v):
 v=np.array(v);rng=np.random.default_rng(20261016);b=v[rng.integers(0,len(v),(20000,len(v)))].mean(1);return dict(mean=float(v.mean()),ci95=np.quantile(b,[.025,.975]).tolist(),values=v.tolist(),independent_blocks=len(v),exploratory=True)
summary=[];comparisons=[]
for event in range(3):
 for policy in ['N','T','M']:
  z=[x for x in rows if not x['qualification'] and x['event']==event and x['policy']==policy and x['role']=='primary']
  if z:summary.append(dict(event=event,policy=policy,ready_ms=ci([x['ready_ms'] for x in z]),event_ms=ci([x['event_ms'] for x in z]),batch_ms=ci([x['batch_ms'] for x in z])))
 for baseline in ['N','T']:
  a={x['block']:x for x in rows if not x['qualification'] and x['event']==event and x['policy']=='M' and x['role']=='primary'};b={x['block']:x for x in rows if not x['qualification'] and x['event']==event and x['policy']==baseline and x['role']=='primary'};ids=sorted(set(a)&set(b))
  for metric in ['ready_ms','event_ms','batch_ms']:
   if not ids:continue
   v=np.array([a[i][metric]/b[i][metric] for i in ids]);z=ci(np.log(v));z.update(mean=float(np.exp(z['mean'])),ci95=np.exp(z['ci95']).tolist(),values=v.tolist());comparisons.append(dict(event=event,method='M',baseline=baseline,metric=metric,ratio=z))
write(r/'derived/LIFECYCLE_ANALYSIS.json',dict(generated_at=utc(),status='COMPLETE' if sum(not x['qualification'] for x in events)==12 else 'PARTIAL',events=events,rows=rows,summary=summary,comparisons=comparisons,saved_full_output_checks=checks,formal_primary_sessions=sum(not x['qualification'] and x['role']=='primary' for x in rows),scope='Actual GPU allocation events inside one live primary context perblock, same synthetic compiled consumer as micro. Fresh calibration eachgeneration; no previouspointer/map used. Not real-model graph-update latency. No second-power experiment.'))
print('lifecycle',len(events),'events',checks,'full-output checks')
