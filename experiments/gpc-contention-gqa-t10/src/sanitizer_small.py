from gqa_runtime import *
from micro_runtime import Micro
import os
folder=Path(os.environ['T10_WORKER_DIR']);c=Control();p=read(RUN/'freeze/resource_sets.json')['blocks'][0]['placements'];resources=[c.create(p[0]['foreground_sm_ids']),c.create(p[-1]['foreground_sm_ids'])];checks=[]
for recipe in ['HOT2_DEFAULT','HOT2_CG','STREAM32_DEFAULT','STREAM32_CG','STREAM128_CG','REG_FMA']:
 for grid in [40,160]:
  d=Micro(recipe,grid,193000000+grid)
  for g in resources:c.current(g);d.op(0)(c.stream(g));c.sync(g);c.current(0);checks.append(dict(recipe=recipe,grid=grid,**d.check(0)))
  del d;gc.collect();torch.cuda.empty_cache()
for G,L in [(4,31),(8,63)]:
 case=dict(id='GQA4_SHORT' if G==4 else 'GQA8_LONG',B=1,H=G*2,HK=2,D=128,L=L,lengths=[L]);d=GQAData(case,193100000+L,0)
 for g in resources:
  for append in [False,True]:
   d.reset();j=GQAJob(d,append,'E56');c.current(g);j.op(1)(c.stream(g));c.sync(g);c.current(0);checks.append(dict(case=case['id'],append=append,**d.check_mode(append,1)))
 d.close()
for g in resources:c.drop(g)
write(folder/'CHECKS.json',checks);print('SMALL_SANITIZER_NUMERICAL_PASS',len(checks),flush=True)
