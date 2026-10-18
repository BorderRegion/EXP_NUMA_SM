"""Same original cubin AND same mapping-buffer VA across all policies.

Only benchmark configuration changes the table. Upload is recorded separately;
a deployed fixed schedule uploads once per plan, not once per request.
"""
from soft_runtime import *
import sys
class CommonMapJob(SoftJob):
 def __init__(self,d,slot,policy,page=0):
  self.sfpolicy=policy;self.page=page;self.flagtrace=False;self.mapping=d.maps[page,policy if policy!='NATIVE' else 'IDENTITY'];self.activate_ms=[]
  self.a=(P*6)(d.x[slot].data_ptr(),d.y.data_ptr(),d.flags.data_ptr(),d.common_map.data_ptr(),d.trace.data_ptr(),d.partial.data_ptr());self.c=(I*4)(d.V,int(policy!='NATIVE'),page,0);self.d=d;self.activate();Job.__init__(self,d,slot,'COMMON_MAP')
 def activate(self):
  t=time.perf_counter();self.d.common_map.copy_(self.mapping);torch.cuda.synchronize();self.activate_ms.append((time.perf_counter()-t)*1000)
 def run(self,n=1):self.activate();return Job.run(self,n)
def run(out,process):
 rng=np.random.default_rng(110000000+process);checks=[]
 for V in rng.permutation([32768,65536,131072,262144]):
  V=int(V);d=SoftData(V,110000000+process*100000+V);d.common_map=torch.empty(56,device='cuda',dtype=torch.int32);case='VOCAB_'+str(V)
  for page in rng.permutation([0,17,257]):
   page=int(page);q=out/case/f'offset_{page}';q.mkdir(parents=True);names=['MINIMAX','IDENTITY','RANDOM','WORST','WRONG_ADDRESS','NATIVE'];jobs={n:[CommonMapJob(d,s,n,page) for s in range(4)] for n in names}
   write(q/'mapping.json',d.meta);write(q/'configs.json',dict(page=page,common_map_va=d.common_map.data_ptr(),all_job_map_pointers=[int(j.a[3]) for js in jobs.values() for j in js]));rows=[]
   for n,js in jobs.items():
    for s,j in enumerate(js):checks.append(dict(case=case,page=page,policy=n,slot=s,when='before',**j.check()))
   def observe(name,stage,b,pos,n):
    begin=time.monotonic_ns();vv=jobs[name][b%4].run(n);end=time.monotonic_ns()
    for i,v in enumerate(vv):rows.append(dict(case=case,offset=page,phase=stage,block=b,position=pos,label=name,slot=b%4,request=i,gpu_us=v[0],host_us=v[1],begin_ns=begin,end_ns=end))
   until=time.monotonic()+.15;b=0
   while time.monotonic()<until:
    for pos,n in enumerate(rng.permutation(names)):observe(n,'conditioning',b,pos,1)
    b+=1
   for b in range(24):
    for pos,n in enumerate(rng.permutation(names)):observe(n,'test',b,pos,12)
    save_rows(q/'requests.csv.gz',rows)
   for n,js in jobs.items():
    for s,j in enumerate(js):checks.append(dict(case=case,page=page,policy=n,slot=s,when='after',**j.check()))
   write(q/'configuration_upload_ms.json',{n:[j.activate_ms for j in js] for n,js in jobs.items()})
   for js in jobs.values():
    for j in js:j.close()
   write(out/'numerical.json',checks);write(q/'complete.json',dict(status='PASS',test_requests=24*12*len(names)));print(process,case,page,'PASS',flush=True)
  d.close()
 write(out/'complete.json',dict(status='PASS'))
if __name__=='__main__':run(Path(sys.argv[1]),int(sys.argv[2]))
