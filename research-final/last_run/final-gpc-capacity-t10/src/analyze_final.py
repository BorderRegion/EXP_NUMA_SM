"""CPU-only arithmetic audit, block comparisons and alias expansion."""
from common import *
import gzip,math,statistics,collections

def gm(v):return math.exp(statistics.mean(math.log(x) for x in v))
all_phases=[];audit=[];micro=[];app=[];gqa=[];aa=[];allrequests=0;incomplete=[]
for folder in sorted((RUN/'raw').iterdir()):
 if not (folder/'PHASES.json').exists() or not (folder/'REQUESTS.json.gz').exists():continue
 if read(folder/'manifest.json')['status']!='COMPLETED':
  incomplete.append(dict(worker=folder.name,reason='incomplete failed worker retained, not selected',capacity=read(folder/'CAPACITY.json') if (folder/'CAPACITY.json').exists() else None));continue
 ph=read(folder/'PHASES.json')
 with gzip.open(folder/'REQUESTS.json.gz','rt') as f:rows=json.load(f)
 allrequests+=len(rows)
 for p in ph:
  if p.get('status')=='STRUCTURAL_ALIAS':continue
  if 'resource' in p:rr=[x for x in rows if x['resource']==p['resource']]
  elif 'case' in p:rr=[x for x in rows if all(x[k]==p[k] for k in ['case','scope','action'])]
  else:rr=[x for x in rows if all(x[k]==p[k] for k in ['recipe','grid','gpc','sm_count','action'])]
  assert len(rr)==p['requests'],(folder,p,len(rr))
  for k in ['gpu_us','ready_us']:
   avg=statistics.mean(x[k] for x in rr);assert math.isclose(avg,p[k],rel_tol=1e-12,abs_tol=1e-9),(folder,k,avg,p[k])
  audit.append(dict(worker=folder.name,phase=p,raw_rows=len(rr),status='MEAN_RECOMPUTED'))
 for p in ph:
  q=dict(p,worker=folder.name)
  if q.get('status')=='STRUCTURAL_ALIAS':
   target=next(x for x in ph if x.get('case')==q['case'] and x.get('scope')==q['scope'] and x['action']==q['alias_of'])
   assert target['status']=='MEASURED'
   for k in ['gpu_us','ready_us','batch32_gpu_us','batch32_ready_us','requests']:q[k]=target[k]
  all_phases.append(q)
  if folder.name.startswith('P2_LIMITED_MICRO'):micro.append(q)
  if folder.name.startswith('P2_LIMITED_GQA'):gqa.append(q)
  if folder.name.startswith('P4_LIMITED'):app.append(q)
 # Same graph repeated across ABBA window, preserved as descriptive sensitivity.
 groups=collections.defaultdict(list)
 for x in rows:
  if 'comparison' in x:key=(x['case'],x['scope'],x['comparison'],x['action'])
  elif 'recipe' in x:key=(x['recipe'],x['grid'],x['gpc'],x['sm_count'],x['action'])
  else:continue
  groups[key].append(x)
 for key,rr in groups.items():
  segs=sorted({x['segment'] for x in rr})
  if len(segs)==2:
   v=[statistics.mean(x['ready_us'] for x in rr if x['segment']==s) for s in segs];aa.append(dict(worker=folder.name,key=list(key),segment_ready_us=v,later_over_earlier_percent=100*(v[1]/v[0]-1)))
weights=read(RUN/'freeze/CAP_WEIGHTS.json');comparisons=[]
for case,scope in sorted({(x['case'],x['scope']) for x in app}):
 for cand,ref in [('CAP','N19'),('CAP',weights['best_simple'][case+':'+scope]),('CAP','SM_PROP'),('CAP','EQUAL_GPC'),('CAP','WRONG_CAP'),('E56_DIRECT','N19'),('SM_PROP','E56_DIRECT')]:
  for metric in ['ready_us','gpu_us','batch32_ready_us','batch32_gpu_us']:
   blocks=[]
   for b in range(2):
    a=next(x for x in app if x['case']==case and x['scope']==scope and x['block']==b and x['action']==cand);r=next(x for x in app if x['case']==case and x['scope']==scope and x['block']==b and x['action']==ref)
    akey=a.get('alias_of',cand);rkey=r.get('alias_of',ref);blocks.append(dict(block=b,candidate=a[metric],reference=r[metric],ratio=a[metric]/r[metric],structural_alias=akey==rkey))
   ratio=gm([v['ratio'] for v in blocks]);comparisons.append(dict(case=case,scope=scope,candidate=cand,reference=ref,metric=metric,ratio=ratio,time_change_percent=100*(ratio-1),blocks=blocks,faster_blocks=sum(x['ratio']<1 for x in blocks),ci=None,inference='TWO_DYNAMIC_STATE_BLOCKS_DESCRIPTIVE_ONLY'))
curves=[]
for p in micro:
 if p['action']!='SUBSET':continue
 curves.append(dict(block=p['block'],recipe=p['recipe'],grid=p['grid'],gpc=p['gpc'],sm_count=p['sm_count'],logical_work=p['logical_work'],unit=p['unit'],gpu_us=p['gpu_us'],ready_us=p['ready_us'],total_service_per_us=p['logical_work']/p['gpu_us'],service_per_sm_us=p['logical_work']/p['gpu_us']/p['sm_count']))
ratios=[]
for recipe in sorted({x['recipe'] for x in curves}):
 blocks=[]
 for b in range(2):
  a=next(x for x in curves if x['gpc']==1 and x['sm_count']==12 and x['recipe']==recipe and x['block']==b);r=next(x for x in curves if x['gpc']==1 and x['sm_count']==10 and x['recipe']==recipe and x['block']==b)
  blocks.append(dict(block=b,total_capacity_12_over_10=a['total_service_per_us']/r['total_service_per_us'],per_sm_12_over_10=a['service_per_sm_us']/r['service_per_sm_us'],t10_gpu_us=r['gpu_us'],t12_gpu_us=a['gpu_us']))
 ratios.append(dict(recipe=recipe,blocks=blocks,total_capacity_ratio=gm([x['total_capacity_12_over_10'] for x in blocks]),inference='LIMITED_DESCRIPTION_NO_SATURATION_CLAIM'))
write(RUN/'derived/ALL_PHASES.json',all_phases);write(RUN/'derived/RAW_MEAN_AUDIT.json',dict(status='PASS',measured_phases=len(audit),requests=allrequests,phases=audit));write(RUN/'derived/APPLICATION_COMPARISONS.json',comparisons);write(RUN/'derived/GPC_CURVES.json',dict(curves=curves,within_gpc_10_12=ratios,gqa_whole_operator=gqa));write(RUN/'derived/AA_SENSITIVITY.json',aa)
write(RUN/'derived/INCOMPLETE_WORKERS.json',incomplete)
print('ANALYSIS_PASS',len(audit),allrequests,len(comparisons))
