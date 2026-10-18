from locality_runtime import *
from locality_plan import LocalityPlan
import sys
class PlanJob(Job):
 def __init__(self,d,slot,plan):self.plan=plan;super().__init__(d,slot,'PLAN')
 def op(self):self.state['out']=self.plan.launch()
out=Path(sys.argv[1]);records=[]
for ci,c in enumerate(read(ROOT/'freeze/PROTOCOL.json')['cases']):
 d=LocalData(c,94000000+ci*101,ring=2)
 for append in [False,True]:
  for slot in range(2):
   for pol in ['LEGACY','PREVIOUS_DEPLOYED','STATIC','COARSE_BLIND','COARSE_MATCH','DEPLOY']:
    t=time.perf_counter();plan=LocalityPlan(d.q[slot],d.k,d.v,d.table,d.length,d.nk if append else None,d.nv if append else None,policy=pol);wall=(time.perf_counter()-t)*1000
    job=PlanJob(d,slot,plan);job.run(12);num=job.check();assert not plan.counter.count_nonzero().item();nk=sum(x['type']==0 for x in job.dag['nodes']);f=bool(plan.cfg[7]);expected=(1 if f else 2)+(append and not plan.previous_fused);assert nk==expected
    records.append(dict(case=c['id'],append=append,slot=slot,policy=pol,resolved=plan.policy,setup_ms=plan.setup_ms,constructor_wall_ms=wall,kernel_count=nk,graph=job.dag,**num));job.close();del plan
 d.close();write(out/'verification.json',records)
write(out/'complete.json',dict(status='PASS',checks=len(records)));print('PUBLIC_API_PASS',len(records))
