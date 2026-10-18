import json,math
from collections import defaultdict
import numpy as np
from common import *
r=runroot();results=[]
for key in ['dev_0','dev_1','confirm_2','confirm_3','confirm_4','confirm_5']:
 p=r/'raw'/key/'analysis.json'
 if p.exists():results.append((key,json.loads(p.read_text())))
def interval(v):
 v=np.array([x for x in v if x is not None and math.isfinite(x)],dtype=float)
 if not len(v):return dict(mean=None,ci95=[None,None],independent_allocations=0,values=[],exploratory=True)
 rng=np.random.default_rng(20261016);means=v[rng.integers(0,len(v),(20000,len(v)))].mean(1)
 return dict(mean=float(v.mean()),ci95=np.quantile(means,[.025,.975]).tolist(),independent_allocations=len(v),values=v.tolist(),exploratory=True)
groups=defaultdict(list);smgroups=defaultdict(list);crosses=defaultdict(list);same_payload=defaultdict(list)
for name,x in results:
 if not name.startswith('confirm'):continue
 for c in x['conditions']:
  key=tuple(c[k] for k in ['bytes','cg','concurrent','mode','cache']);groups[key].append(c)
 for c in x['sm_conditions']:
  key=tuple(c[k] for k in ['bytes','cg','concurrent','mode','cache']);smgroups[key].append(c)
 for c in x['cross']:
  key=tuple(c[k] for k in ['bytes','cache','layout_swap']);crosses[key].append(c)
 for c in x.get('same_payload_cross',[]):
  key=tuple(c[k] for k in ['bytes','cache','logical_payload_half']);same_payload[key].append(c)
summary=[]
for key,cells in groups.items():
 item=dict(zip(['bytes','cg','concurrent','mode','cache'],key));item['late_signed_log_effect']=interval([c['late_signed_log_effect'] for c in cells]);item['early_late_group_residual_correlation']=interval([c['early_late_residual_correlation'] for c in cells]);item['home_agreement']=interval([c['early_late_home_agreement'] for c in cells]);sc=smgroups[key];vals=[c['early_late_sm_address_residual_correlation'] for c in sc if c['early_late_sm_address_residual_correlation'] is not None]
 item['early_late_sm_residual_correlation']=interval(vals) if vals else None;item['sm_common_coverage']=[c['common_cell_coverage'] for c in sc];summary.append(item)
cross=[]
for key,cells in crosses.items():
 item=dict(zip(['bytes','cache','layout_swap'],key));item['cell_log_interaction']=interval([c['cell_log_interaction_mean'] for c in cells]);item['joint_log_reverse_over_match']=interval([math.log(c['joint_reverse_over_match']) for c in cells]);cross.append(item)
payload=[dict(zip(['bytes','cache','logical_payload_half'],key),log_interaction=interval([c['log_interaction_mean'] for c in cells])) for key,cells in same_payload.items()]
write(r/'derived/P1_SUMMARY.json',dict(generated_at=utc(),status='COMPLETE' if len(results)==6 else 'PARTIAL',independent_main_allocations=len(results),record_count=sum(x['record_count'] for _,x in results),epoch_count=sum(x['epoch_count'] for _,x in results),confirmation_conditions=summary,confirmation_cross=cross,confirmation_same_payload_cross=payload,all_fits={k:x['fits'] for k,x in results},inference_scope='Bootstrap independent allocation blocks; millions of CTA samples are not independent experimental units; all intervals exploratory; no percent threshold used to skip actual swaps.'))
for c in summary:
 if c['cg']==c['concurrent']==1 and c['mode']==c['cache']==0:print(json.dumps(c))
