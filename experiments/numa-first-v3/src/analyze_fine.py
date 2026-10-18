"""Post-hoc finer-control analysis, independent block intervals, all conditions retained."""
import csv,json,math
from collections import defaultdict
import numpy as np
from common import *
from analyze_probe import DT
def read(p):return list(csv.DictReader(p.open()))
def ci(v):
 v=np.asarray(v);rng=np.random.default_rng(2026101677);boot=v[rng.integers(0,len(v),(20000,len(v)))].mean(1);return dict(mean=float(v.mean()),ci95=np.quantile(boot,[.025,.975]).tolist(),values=v.tolist(),independent_allocations=len(v),exploratory=True)
def analyze(p):
 meta=read(p/'epochs.csv');raw=np.memmap(p/'records.bin',DT,mode='r');lookup=defaultdict(lambda:np.zeros((8,28,64)));roster=read(p/'rosters.csv');assert all(int(x['configured_sms'])==2 for x in roster)
 for e in meta:
  start=int(e['raw_record_offset']);v=raw[start:start+512];key=tuple(int(e[k]) for k in ['bytes','cache','cg','mode']);rd,g=int(e['round']),int(e['group']);lookup[key][rd,g]=np.bincount(v['region'],weights=np.log(v['ticks'].astype(float)),minlength=64)/8
 fits=read(p/'fits.csv');conditions=[];maps=[];mapkeys=[]
 for f in fits:
  scope=f['control_scope'];size,g0,g1,mask,bias=[int(f[k]) for k in ['bytes','group0','group1','mask','bias']];sign=np.array([1 if (((r&mask).bit_count()%2)^bias)==0 else -1 for r in range(64)])
  for key,y in lookup.items():
   if key[0]!=size:continue
   res=y-y.mean(2,keepdims=True)-y.mean(1,keepdims=True)+y.mean((1,2),keepdims=True);early=res[:4].mean(0);late=res[4:].mean(0);
   if scope=='PAIR4SM':diff=y[:,g1]-y[:,g0]
   else:
    membership=read(p/f'merged_{size}.csv');m0=sorted({int(x['fine_group']) for x in membership if int(x['merged_group'])==g0});m1=sorted({int(x['fine_group']) for x in membership if int(x['merged_group'])==g1});diff=y[:,m1].mean(1)-y[:,m0].mean(1)
   diff-=diff.mean(1,keepdims=True)
   conditions.append(dict(zip(['bytes','cache','cg','mode'],key),control_scope=scope,group0=g0,group1=g1,mask=mask,bias=bias,early_late_all_group_address_correlation=float(np.corrcoef(early.ravel(),late.ravel())[0,1]),early_late_selected_pair_correlation=float(np.corrcoef(diff[:4].mean(0),diff[4:].mean(0))[0,1]),late_signed_log_effect=float((diff[4:]*sign).mean()),round_effects=(diff*sign).mean(1).tolist(),content_xor_effect=[float((diff[i::2]*sign).mean()) for i in [0,1]]));maps.append(res);mapkeys.append(key)
 np.savez_compressed(p/'fine_maps.npz',keys=np.array(mapkeys),residual=np.array(maps));cr=read(p/'cross.csv');assert all(x['checksum_pass']=='1' for x in cr);cross=[];payload=[]
 for size,scope,cache,mode in sorted({(int(x['bytes']),x['control_scope'],int(x['cache']),int(x['mode'])) for x in cr}):
  cells={};joint={}
  for x in cr:
   if (int(x['bytes']),x['control_scope'],int(x['cache']),int(x['mode']))!=(size,scope,cache,mode):continue
   rd,lay,g,d,sw=[int(x[k]) for k in ['round','layout_swap','group','data_class','compute_swap']]
   if x['kind']=='CELL':cells[rd,lay,g,d]=float(x['group_event_ms'])
   else:joint[rd,lay,sw]=float(x['event_ms'])
  for lay in [0,1]:
   ratios=[math.log(joint[rd,lay,1]/joint[rd,lay,0]) for rd in range(8)];cross.append(dict(bytes=size,control_scope=scope,cache=cache,mode=mode,layout_swap=lay,joint_log_reverse_over_match=float(np.mean(ratios)),round_values=ratios))
  for half in [0,1]:
   vals=[.5*(math.log(cells[rd,half^1,0,1])+math.log(cells[rd,half^0,1,0])-math.log(cells[rd,half^0,0,0])-math.log(cells[rd,half^1,1,1])) for rd in range(8)];payload.append(dict(bytes=size,control_scope=scope,cache=cache,mode=mode,logical_half=half,log_interaction=float(np.mean(vals)),round_values=vals))
 result=dict(status='PASS',records=len(raw),fits=fits,conditions=conditions,cross=cross,same_payload_cross=payload,rosters=roster,post_hoc=True);write(p/'analysis.json',result);return result
if __name__=='__main__':
 import sys
 r=runroot();items={}
 for i in range(4):
  p=r/'raw'/f'fine_shift_{i}'
  if (p/'correctness.json').exists():items[i]=analyze(p)
 groups=defaultdict(list);cross=defaultdict(list);payload=defaultdict(list)
 for i,x in items.items():
  if i==0:continue
  for c in x['conditions']:groups[tuple(c[k] for k in ['bytes','control_scope','cache','cg','mode'])].append(c)
  for c in x['cross']:cross[tuple(c[k] for k in ['bytes','control_scope','cache','mode','layout_swap'])].append(c['joint_log_reverse_over_match'])
  for c in x['same_payload_cross']:payload[tuple(c[k] for k in ['bytes','control_scope','cache','mode','logical_half'])].append(c['log_interaction'])
 summary=[dict(zip(['bytes','control_scope','cache','cg','mode'],k),late_effect=ci([c['late_signed_log_effect'] for c in v]),map_stability=ci([c['early_late_all_group_address_correlation'] for c in v])) for k,v in groups.items()]
 legacy=r/'raw/fine_0'
 if (legacy/'correctness.json').exists():analyze(legacy)
 result=dict(status='COMPLETE' if len(items)==4 else 'PARTIAL',allocations=len(items),records=sum(x['records'] for x in items.values()),fits={i:x['fits'] for i,x in items.items()},conditions=summary,cross=[dict(zip(['bytes','control_scope','cache','mode','layout_swap'],k),effect=ci(v)) for k,v in cross.items()],same_payload_cross=[dict(zip(['bytes','control_scope','cache','mode','logical_half'],k),effect=ci(v)) for k,v in payload.items()],scope='Post-hoc public 2-SM control refinement with separate equivalent shift/mask cubin. Three independent confirmation allocations, all-pair fit only early calibration; do not pool with pre-frozen P1.');write(r/'derived/FINE_SUMMARY.json',result);print(result['status'],result['allocations'])
