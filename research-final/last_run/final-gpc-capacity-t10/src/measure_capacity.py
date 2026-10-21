from range_runtime import *
from micro_runtime import Micro
import random
folder=Path(os.environ['T10_WORKER_DIR']);block=int(sys.argv[1]);limited='--limited' in sys.argv
c=Control();plan=read(RUN/'freeze/resource_subsets.json')['resource_sets'];resources=[x for x in plan if x['block']==block]
if limited:resources=[x for x in resources if (x['gpc'],x['sm_count']) in [(0,10),(1,8),(1,10),(1,12),(2,12)]]
recipes=['HOT2_CG','STREAM128_CG','REG_FMA'] if limited else ['HOT2_DEFAULT','HOT2_CG','STREAM32_CG','STREAM128_CG','REG_FMA'];grids=[240] if limited else [120,240]
rows=[];phase=[];checks=[];rng=random.Random(211300+block);rng.shuffle(resources)
class MP:
 def __init__(self,m,g):self.m=m;self.graphs=[c.capture(g,[m.op(s)]) for s in range(4)]
 def run(self,n,start=0):return c.run(self.graphs[start:]+self.graphs[:start],n)
 def batch(self,n=32,start=0):
  out=np.empty(2);gs=self.graphs[start:]+self.graphs[:start];ck(z.gc_batch((P*4)(*gs),4,n,out.ctypes.data_as(DP)));return out
 def close(self):c.graph_drop(self.graphs)
def save():
 write(folder/'PHASES.json',phase);write(folder/'CHECKS.json',checks)
 with gzip.open(folder/'REQUESTS.json.gz','wt') as f:json.dump(rows,f)
for recipe in recipes:
 for grid in grids:
  m=Micro(recipe,grid,211400+block);base=MP(m,0)
  for s in range(4):base.run(1,s);checks.append(dict(recipe=recipe,grid=grid,group='PRIMARY56',slot=s,check=m.check(s)))
  warm(base);pilot=base.run(8);n=max(8,min(128,int(math.ceil(5000/np.median(pilot[:,1])))));n=4*int(math.ceil(n/4));write(folder/f'PILOT_{recipe}_{grid}.json',dict(replays=n,values=pilot.tolist()))
  for p in resources:
   g=c.create(p['sm_ids']);c.verify(g,p['sm_ids']);q=MP(m,g)
   for s in range(4):q.run(1,s);checks.append(dict(recipe=recipe,grid=grid,gpc=p['gpc'],sm_count=p['sm_count'],slot=s,check=m.check(s)))
   wa=warm(base);wb=warm(q);order=['A','B','B','A'] if (block+p['gpc']+p['sm_count'])%2==0 else ['B','A','A','B'];values={'A':[],'B':[]};t0=utc()
   for segment,label in enumerate(order):
    a=(base if label=='A' else q).run(n,segment%4);values[label].append(a)
    for i,v in enumerate(a):rows.append(dict(block=block,recipe=recipe,grid=grid,gpc=p['gpc'],sm_count=p['sm_count'],action='PRIMARY56' if label=='A' else 'SUBSET',segment=segment,slot=(segment+i)%4,gpu_us=float(v[0]),ready_us=float(v[1])))
   for label in ['A','B']:
    v=np.concatenate(values[label]);phase.append(dict(block=block,recipe=recipe,grid=grid,gpc=p['gpc'],sm_count=p['sm_count'],action='PRIMARY56' if label=='A' else 'SUBSET',gpu_us=float(v[:,0].mean()),ready_us=float(v[:,1].mean()),requests=len(v),start_utc=t0,end_utc=utc(),logical_work=(grid*128*8*128*2 if m.compute else m.nbytes*m.passes),unit='FLOPs' if m.compute else 'logical_bytes',sm_ids=p['sm_ids'],warm=[wa,wb]))
   q.close();c.drop(g);save()
  base.close();del m;gc.collect();torch.cuda.empty_cache()
  print('MICRO_COMPLETE',block,recipe,grid,flush=True)
write(folder/'DONE.json',dict(status='PASS',phase_labels=len(phase),limited=limited))
