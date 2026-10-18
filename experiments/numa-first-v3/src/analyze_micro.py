"""Full saved-output and placement checks, then block-level Graph micro comparisons."""
import csv,json,math
from collections import defaultdict
import numpy as np
from common import *
from analyze_probe import DT
r=runroot();ledger=[json.loads(x) for x in (r/'ledger.jsonl').read_text().splitlines()]
def read(p):return list(csv.DictReader(p.open()))
def interval(v,log=False,alpha=.05):
 v=np.asarray(v,dtype=float);z=np.log(v) if log else v;rng=np.random.default_rng(20261016);bs=z[rng.integers(0,len(z),(20000,len(z)))].mean(1);mean=z.mean();ci=np.quantile(bs,[alpha/2,1-alpha/2]);return dict(estimate=float(np.exp(mean) if log else mean),ci95=(np.exp(ci) if log else ci).tolist(),values=v.tolist(),independent_blocks=len(v),confidence=1-alpha,exploratory=True)
def slot(j,d,mask,bias):
 p=(mask&-mask).bit_length()-1;u=(j&((1<<p)-1))|((j>>p)<<(p+1));return u|((((u&mask).bit_count()%2)^bias^d)<<p)
rows=[];costs=[];checks_count=0;worker_summary=[]
for w in ledger:
 if w['key'] not in ['micro_development','micro_qualification','micro_order_qualification'] and not w['key'].startswith('micro_b'):continue
 if w['status']!='COMPLETED':continue
 p=Path(w['out']);block=-3 if w['key']=='micro_order_qualification' else -2 if w['key']=='micro_qualification' else -1 if w['key']=='micro_development' else int(w['key'].split('_b')[-1]);stage='QUALIFICATION' if block in [-3,-2] else 'DEVELOPMENT' if block==-1 else 'FORMAL';fits={int(x['bytes']):x for x in read(p/'fits.csv')};membership=read(p/'membership.csv');outputs=np.fromfile(p/'logical_outputs.bin',dtype='<u8');diag=np.fromfile(p/'diagnostic_outputs.bin',dtype=DT);ck=read(p/'checks.csv');assert len(outputs)==len(diag)==len(ck)*64
 for c in ck:
  size,mode=int(c['bytes']),int(c['mode']);method=c['policy'];off=int(c['raw_u64_offset']);assert off==int(c['raw_diag_record_offset']);v=outputs[off:off+64];d=diag[off:off+64];expected=np.array([int(x['sum_onepass']) for x in read(p/f'expected_{size}.csv')],dtype=np.uint64)*(4 if mode==2 else 1);assert np.array_equal(v,expected) and np.array_equal(v,d['sum']);assert np.array_equal(d['sm_begin'],d['sm_end']);assert np.array_equal(d['position'],np.arange(64))
  mask,bias=int(fits[size]['mask']),int(fits[size]['bias']);is_colored=method in ['Y','M','P'];want=[slot(j%32,j//32,mask,bias) if is_colored else j for j in range(64)];assert np.array_equal(d['region'],want)
  if method!='N':
   kind='LEARNED' if method in ['T','X','M','P'] else 'NEUTRAL';m=[x for x in membership if int(x['bytes'])==size and x['kind']==kind];groups=sorted({int(x['group']) for x in m});assert len(groups)==2;sets=[{int(x['actual_sm']) for x in m if int(x['group'])==g} for g in groups];assert len(sets[0])==len(sets[1])==28 and not sets[0]&sets[1]
   for j in range(64):
    dc=j%2 if method=='B' else ((j&mask).bit_count()%2)^bias if method=='T' else j//32;dc^=int(method=='P');assert int(d['sm_begin'][j]) in sets[dc]
  checks_count+=1
 sample=defaultdict(list)
 for x in read(p/'samples.csv'):sample[tuple(x[k] for k in ['bytes','mode','policy','role'])].append(x)
 for q in read(p/'phases.csv'):
  k=tuple(q[k] for k in ['bytes','mode','policy','role']);s=sample[k];assert len(s)==(8 if stage=='QUALIFICATION' else 128);event=np.array([float(x['event_ms']) for x in s]);ready=np.array([float(x['cpu_ready_ms']) for x in s]);prep=np.array([float(x['cache_prepare_ms']) for x in s]);rows.append(dict(stage=stage,block=block,bytes=int(q['bytes']),mode=int(q['mode']),policy=q['policy'],role=q['role'],event_ms=float(event.mean()),ready_ms=float(ready.mean()),total_ready_ms=float((ready+prep).mean()),ready_p50_ms=float(np.quantile(ready,.5)),ready_p99_descriptive_ms=float(np.quantile(ready,.99)),batch_ms=float(q['batch_event_ms'])/int(q['batch_repeats']),batch_repeats=int(q['batch_repeats']),batch_event_ms=float(q['batch_event_ms']),graph_nodes=int(q['graph_nodes']),graph_build_ms=float(q['graph_build_ms']),layout_copy_ms=float(q['layout_copy_ms']),requests=len(s),source=str(p.relative_to(r))))
 setup=json.loads((p/'setup_costs.json').read_text())
 for size,f in fits.items():costs.append(dict(stage=stage,block=block,bytes=size,setup=setup,calibration=f,layout=json.loads((p/f'layout_cost_{size}.json').read_text())))
 worker_summary.append(dict(key=w['key'],block=block,stage=stage,full_output_comparisons=len(ck),fit_masks={size:int(f['mask']) for size,f in fits.items()}))
groups=defaultdict(dict)
for x in rows:
 if x['stage']=='FORMAL' and x['role']=='primary':groups[x['bytes'],x['mode'],x['policy']][x['block']]=x
summary=[];comparisons=[]
for key,blocks in groups.items():summary.append(dict(zip(['bytes','mode','policy'],key),**{k:interval([v[k] for v in blocks.values()]) for k in ['event_ms','ready_ms','total_ready_ms','batch_ms']}))
for size,mode in sorted({k[:2] for k in groups}):
 for method,base in [('E','N'),('B','N'),('X','N'),('Y','N'),('T','N'),('M','N'),('M','T'),('P','M'),('M','E'),('M','B')]:
  a,b=groups[size,mode,method],groups[size,mode,base];ids=sorted(set(a)&set(b))
  for metric in ['event_ms','ready_ms','total_ready_ms','batch_ms']:
   comparisons.append(dict(bytes=size,mode=mode,method=method,baseline=base,metric=metric,ratio=interval([a[i][metric]/b[i][metric] for i in ids],True,.025 if method=='M' and base in ['N','T'] and metric=='total_ready_ms' else .05),absolute_difference_ms=interval([a[i][metric]-b[i][metric] for i in ids])))
breakeven=[]
for c in costs:
 if c['stage']!='FORMAL':continue
 size,block=c['bytes'],c['block']
 for mode in range(3):
  for baseline in ['N','T']:
   a=groups[size,mode,'M'][block];b=groups[size,mode,baseline][block]
   extra=c['layout']['additional_host_color_layout_ms']+(a['layout_copy_ms']-b['layout_copy_ms'])+(a['graph_build_ms']-b['graph_build_ms'])
   if baseline=='N':extra+=c['setup']['fine_green_groups_create_ms']+float(c['calibration']['calibration_total_ms'])
   saving=b['total_ready_ms']-a['total_ready_ms'];breakeven.append(dict(bytes=size,mode=mode,block=block,baseline=baseline,incremental_observed_setup_estimate_ms=extra,ready_saving_ms=saving,requests_to_amortize=max(0,math.ceil(extra/saving)) if saving>0 else None,scope='Synthetic observed components only; calibration_total contains fit and matched-context creation. M/N adds28fine-group setup and calibration; M/T shares these costs. Both add host relayout and measured upload/Graph setup differences. Common input/buffers and primary initialization shared. Module loading not isolated; not real application deployment cost.'))
anchors=[]
for size,mode in sorted({(x['bytes'],x['mode']) for x in rows if x['stage']=='FORMAL'}):
 for block in sorted({x['block'] for x in rows if x['stage']=='FORMAL'}):
  z={x['role']:x for x in rows if x['stage']=='FORMAL' and x['bytes']==size and x['mode']==mode and x['block']==block and x['role'].startswith('anchor')}
  if 'anchor_head' in z and 'anchor_tail' in z:anchors.append(dict(bytes=size,mode=mode,block=block,tail_head_ready_ratio=z['anchor_tail']['total_ready_ms']/z['anchor_head']['total_ready_ms'],tail_head_event_ratio=z['anchor_tail']['event_ms']/z['anchor_head']['event_ms']))
bstar=[]
if (r/'B_STAR_FREEZE.json').exists():
 frozen=json.loads((r/'B_STAR_FREEZE.json').read_text())
 for f in frozen['choices']:
  for c in comparisons:
   if c['bytes']==f['bytes'] and c['mode']==f['mode'] and c['method']=='M' and c['baseline']==f['comparator']:bstar.append(dict(c,selected_comparator=f['comparator'],selection='development-only B_STAR_FREEZE.json; alias of existing comparison, not a new independent sample'))
write(r/'derived/MICRO_ANALYSIS.json',dict(generated_at=utc(),status='COMPLETE' if sum(x['stage']=='FORMAL' for x in worker_summary)==8 else 'PARTIAL',workers=worker_summary,full_output_checks=checks_count,rows=rows,summary=summary,comparisons=comparisons,costs=costs,synthetic_break_even=breakeven,anchors=anchors,bstar_comparisons=bstar,M_T_status='Distinct layouts; same calibrated information and physical address sets; T avoids colored data relayout. Explicit M/T comparison.',scope='Controlled synthetic coalesced micro. N is same-body linear full-device baseline, not a production-library application. Per-CTA diagnostic writes present equally in all methods. No proof of physical NUMA/remote traffic.'))
print('micro workers',len(worker_summary),'saved full-output checks',checks_count)
