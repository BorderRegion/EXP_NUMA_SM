"""Actual ordered phases and available telemetry; no interpolation or correction."""
import csv,json
from collections import Counter,defaultdict
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from common import *
r=runroot();led=[json.loads(x) for x in (r/'ledger.jsonl').read_text().splitlines()];rows=[];orders={};native=[]
def read(p):return list(csv.DictReader(p.open()))
def state(t,begin,end,clock):
 selected=[x for x in t if begin<=int(x[clock])<=end];z=dict(samples=len(selected))
 for key in ['temperature_c','power_mw','sm_mhz']:
  a=[float(x[key]) for x in selected if x[key] and not x[key].startswith('NA')];z[key]=dict(min=min(a),mean=float(np.mean(a)),max=max(a)) if a else None
 return z
for w in led:
 if w['status']!='COMPLETED':continue
 p=Path(w['out']);telemetry=read(p/'telemetry.csv')
 if w['key'].startswith('micro_b'):
  block=int(w['key'].split('_b')[-1]);phases=read(p/'phases.csv');groups=defaultdict(list)
  for i,x in enumerate(phases):
   if x['role']=='primary':groups[int(x['bytes']),int(x['mode'])].append(x['policy'])
   rows.append(dict(worker=w['key'],block=block,phase_index=i,bytes=int(x['bytes']),mode=int(x['mode']),policy=x['policy'],role=x['role'],wall_start_ns=int(x['wall_start_ns']),wall_end_ns=int(x['wall_end_ns']),telemetry=state(telemetry,int(x['wall_start_ns']),int(x['wall_end_ns']),'wall_ns')))
  orders[block]={f'{size}_{mode}':v for (size,mode),v in groups.items()}
 if w['key'].startswith('p4_native_b'):
  for f in p.glob('operators/*/result.json'):
   d=json.loads(f.read_text())
   for i,x in enumerate(d['phases']):native.append(dict(worker=w['key'],case=d['case']['id'],phase_index=i,method=x['method'],role=x['role'],state=x['state'],start_monotonic_ns=x['start_monotonic_ns'],measured_start_monotonic_ns=x['measured_start_monotonic_ns'],end_monotonic_ns=x['end_monotonic_ns'],warmup_repeats=x['warmup_repeats'],warmup_event_ms=x['warmup_event_ms'],batch_repeats=x['throughput']['repeats'],batch_event_ms=x['throughput']['event_span_ms'],telemetry=state(telemetry,x['start_monotonic_ns'],x['end_monotonic_ns'],'monotonic_ns')))
balance=[]
for key in sorted({key for x in orders.values() for key in x}):
 matrix=[v[key] for _,v in sorted(orders.items())];policies=['N','E','B','T','X','Y','M','P'];counts=[[sum(row[j]==policy for row in matrix) for j in range(8)] for policy in policies];balanced=len(matrix)==8 and all(v==1 for row in counts for v in row);pairs=Counter((row[j-1],row[j]) for row in matrix for j in range(1,8));pair_balanced=len(matrix)==8 and len(pairs)==56 and set(pairs.values())=={1};balance.append(dict(case=key,blocks=len(matrix),policies=policies,position_counts=counts,all_positions_once=balanced,directed_predecessor_counts={a+'->'+b:v for (a,b),v in pairs.items()},all56directed_pairs_once=pair_balanced))
 if len(matrix)==8:assert balanced and pair_balanced
if orders:
 key=sorted(next(iter(orders.values())))[0];ps=['N','E','B','T','X','Y','M','P'];matrix=np.array([[ps.index(v) for v in q[key]] for _,q in sorted(orders.items())]);fig,ax=plt.subplots(figsize=(9,4.8));ax.imshow(matrix,cmap='tab10',vmin=0,vmax=9,aspect='auto')
 for y in range(len(matrix)):
  for x in range(8):ax.text(x,y,ps[matrix[y,x]],ha='center',va='center',color='white',weight='bold')
 ax.set(xticks=range(8),xticklabels=range(1,9),yticks=range(len(matrix)),yticklabels=[str(x) for x in sorted(orders)],xlabel='Primary strategy position (N anchors excluded)',ylabel='Independent allocation block',title='Actual compiled-micro Williams order: positions and directed predecessor pairs');fig.tight_layout()
 for suffix in ['png','pdf']:fig.savefig(r/'figures'/f'actual_micro_strategy_order.{suffix}',dpi=150,bbox_inches='tight')
 plt.close(fig)
write(r/'derived/PHASE_ORDER_AUDIT.json',dict(generated_at=utc(),micro_orders=orders,position_balance=balance,micro_phase_state=rows,native_phase_state=native,scope='Measured windows only. Native state window includes warmup and batch; micro window excludes warmup.1Hz samples may miss short phases: null is unknown, never filled by interpolation. No temperature/clock performance adjustment.',lifecycle_note='Three fixed events in order. Old learned merged-context handles persist until process destruction, a bounded increase of2per event; therefore between-event timing changes are not an isolated capacity effect.'))
print('phase order',len(orders),'micro blocks;',len(native),'native phases')
