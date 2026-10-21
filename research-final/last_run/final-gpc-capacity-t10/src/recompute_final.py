"""Portable CPU-only recomputation of the new finite campaign. No torch/CUDA import."""
from common import *
import subprocess,sys,gzip,math,statistics
names=['ALL_PHASES.json','RAW_MEAN_AUDIT.json','APPLICATION_COMPARISONS.json','GPC_CURVES.json','AA_SENSITIVITY.json','INCOMPLETE_WORKERS.json','COST_ACCOUNTING.json','PAIR_SPECIFIC_SENSITIVITY.json','PAIRED_PRIMARY_COMPARISONS.json','ALL_CONDITIONS.jsonl']
before={n:sha(RUN/'derived'/n) for n in names}
subprocess.run([sys.executable,str(ROOT/'src/analyze_final.py')],check=True)
subprocess.run([sys.executable,str(ROOT/'src/extra_final.py')],check=True)
subprocess.run([sys.executable,str(ROOT/'src/paired_analysis.py')],check=True)
assert before=={n:sha(RUN/'derived'/n) for n in names},'Derived recomputation mismatch'
frozen=read(RUN/'freeze/CAP_WEIGHTS.json');capacity=[];ph=[];pm=[]
for b in range(2):
 folder=RUN/'raw'/('P3_DEV_0_retry2' if b==0 else 'P3_DEV_1');assert read(folder/'DONE.json')['status']=='PASS';capacity+=read(folder/'CAPACITY.json');ph+=read(folder/'PHASES.json');pm+=read(folder/'PLANS.json')
for key,entry in frozen['weights'].items():
 cid,scope=key.split(':')
 for name in ['ISOLATED','CONCURRENT']:
  recomputed=[]
  for g in [0,1,2,3,5]:
   rr=[r for r in capacity if r['case']==cid and r['scope']==scope and r['kind']==name and r['gpc']==g];assert len(rr)==2
   for r in rr:assert math.isclose(r['span_us'],statistics.mean(r['samples_us']),rel_tol=1e-12);assert math.isclose(r['capacity'],r['proxy_work']/r['span_us'],rel_tol=1e-12)
   recomputed.append(math.exp(statistics.mean(math.log(r['capacity']) for r in rr)))
  assert all(math.isclose(x,y,rel_tol=1e-12) for x,y in zip(recomputed,entry[name.lower()]))
cases=read(ROOT/'input/T10_FINAL_GPC_CAPACITY_AND_ARCHIVE_20261021/plans/cases.json')
for c in cases:
 key=c['id']+':append';anchor=c['weights_from'];scores={a:math.exp(statistics.mean(math.log(r['ready_us']) for r in ph if r['case']==anchor and r['scope']=='append' and r['action']==a)) for a in ['N19','E56_DIRECT','SM_PROP','EQUAL_GPC']};assert min(scores,key=scores.get)==frozen['best_simple'][key]
 assert frozen['replays'][key]==max(r['replays'] for r in pm if r.get('kind')=='PILOT' and r['case']==anchor and r['scope']=='append')
# Frozen task intervals decoded on CPU; all groups cover complete workers exactly once.
sys.path.insert(0,str(ROOT/'input/T10_FINAL_GPC_CAPACITY_AND_ARCHIVE_20261021/tools'))
from plans import task_costs,contiguous_partition
for b in range(2):
 rows=read(RUN/'raw'/f'P4_LIMITED_{b}'/'PLANS.json')
 for r in rows:
  if 'implementation' not in r or r['action']=='N19':continue
  c=next(c for c in cases if c['id']==r['case']);impl=r['implementation'];costs=task_costs(c['lengths'],c['Hkv'],impl['W']);ranges=impl['ranges'];flat=[t for x in ranges for t in range(x['task_begin'],x['task_begin']+x['task_count'])];assert flat==list(range(len(costs)))
  if r['action']!='E56_DIRECT':
   w=[10,12,12,10,12] if r['action']=='SM_PROP' else [1]*5 if r['action']=='EQUAL_GPC' else frozen['weights'][c['weights_from']+':append']['concurrent']
   if r['action']=='WRONG_CAP':w=w[1:]+w[:1]
   assert ranges==contiguous_partition(costs,w)
state_requests=0
for name in ['P1_DYNAMIC_BASE','P1_LOCK_1','P1_LOCK_2','P1_LOCK_3']:
 folder=RUN/'raw'/name
 for recipe in ['GQA_LONG','GEMM','STREAM128']:
  interval=read(folder/(recipe+'_interval.json'))
  with gzip.open(folder/(recipe+'_requests.json.gz'),'rt') as f:rr=json.load(f)
  assert len(rr)==interval['requests'] and interval['elapsed_seconds']>=60 and all(len(r)==2 and min(r)>0 for r in rr);state_requests+=len(rr)
assert not any(x in sys.modules for x in ['torch','gqa_runtime','control'])
print('CPU_RECOMPUTE_PASS: 152 phase means, all frozen capacities/ranges/simple choices, exact derived hashes, state requests',state_requests)
