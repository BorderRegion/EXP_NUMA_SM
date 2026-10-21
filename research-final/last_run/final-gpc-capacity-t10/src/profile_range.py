import os
os.environ['TEARDOWN_CUPTI']='0';os.environ['DISABLE_CUPTI_LAZY_REINIT']='1'
from range_runtime import *
from micro_runtime import Micro
folder=Path(os.environ['T10_WORKER_DIR']);c=Control();gs,_=groups_create(c);d=GQAData(shape('A02'),212000,0);w=read(RUN/'freeze/CAP_WEIGHTS.json')['weights']['A02:append']['concurrent'];plans={};m=Micro('HOT2_CG',240,212001)
class MP:
 def __init__(self,g):self.graphs=[c.capture(g,[m.op(s)]) for s in range(4)]
 def run(self,n,start=0):return c.run(self.graphs[start:]+self.graphs[:start],n)
 def close(self):c.graph_drop(self.graphs)
resource=read(RUN/'freeze/resource_subsets.json')['resource_sets'];ids=[]
for n in [10,12]:
 r=next(p for p in resource if p['block']==0 and p['gpc']==1 and p['sm_count']==n);g=c.create(r['sm_ids']);c.verify(g,r['sm_ids']);ids.append(g);plans['GPC1_N'+str(n)]=MP(g)
plans['E56_DIRECT']=RangePlan(c,d,True,[0],[dict(task_begin=0,task_count=256)]);plans['CAP']=RangePlan(c,d,True,gs,ranges_for(d,w));results=[]
for name,p in plans.items():
 p.run(4)
 with torch.profiler.profile(activities=[torch.profiler.ProfilerActivity.CPU,torch.profiler.ProfilerActivity.CUDA]) as prof:p.run(4)
 path=folder/(name+'.json');prof.export_chrome_trace(str(path));events=read(path)['traceEvents'];kernels=[x for x in events if x.get('cat')=='kernel' and x.get('ph')=='X'];assert kernels
 results.append(dict(name=name,kernels=kernels,kernel_count=len(kernels),trace=path.name,clock_control='NONE; dynamic restored state',cache_control='NONE',replay='4 graph requests, ring4',serialization='only operator output-ready; profiler overhead excluded from formal metrics',hardware_memory_counters=None))
 if name in ['E56_DIRECT','CAP']:d.check_mode(True,3)
 else:m.check(3)
 p.close()
write(folder/'PROFILES.json',results)
for g in ids+gs:c.drop(g)
print('FOUR_DIAGNOSTIC_CAPTURES_PASS',flush=True)
