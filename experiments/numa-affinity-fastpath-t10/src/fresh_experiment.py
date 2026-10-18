from soft_runtime import *
import sys
copy=C.CDLL(str(ROOT/'build/refresh.so'));copy.copy_launch.argtypes=[P,P,I,C.c_ulonglong]
class FreshJob(SoftJob):
 def op(self):
  rc=copy.copy_launch(self.d.source[self.slot].data_ptr(),self.d.x[self.slot].data_ptr(),self.d.V,torch.cuda.current_stream().cuda_stream)
  if rc:raise RuntimeError('copy launch error '+str(rc))
  super().op()
def run(out,process):
 rng=np.random.default_rng(107000000+process);checks=[]
 for V in rng.permutation([32768,65536,131072,262144]):
  V=int(V);d=SoftData(V,107000000+process*100000+V);d.source=[x.clone() for x in d.x];case='VOCAB_'+str(V)
  for page in rng.permutation([0,17,257]):
   page=int(page);q=out/case/f'offset_{page}';q.mkdir(parents=True);names=['MINIMAX','IDENTITY','WRONG_ADDRESS','NATIVE','RANDOM'];jobs={n:[FreshJob(d,s,n,page) for s in range(4)] for n in names}
   write(q/'mapping.json',d.meta);write(q/'graphs.json',{n:[j.dag for j in js] for n,js in jobs.items()});write(q/'configs.json',dict(page=page,policies=names,map_sha256=sha(ROOT/'freeze/SOFTMAX_MAPS.json')))
   for n,js in jobs.items():
    for s,j in enumerate(js):d.x[s].fill_(0);torch.cuda.synchronize();checks.append(dict(case=case,page=page,policy=n,slot=s,when='before',**j.check()))
   rows=[]
   def observe(name,stage,b,pos,n):
    begin=time.monotonic_ns();vv=jobs[name][b%4].run(n);end=time.monotonic_ns()
    for i,v in enumerate(vv):rows.append(dict(case=case,offset=page,phase=stage,block=b,position=pos,label=name,slot=b%4,request=i,gpu_us=v[0],host_us=v[1],begin_ns=begin,end_ns=end))
   until=time.monotonic()+.15;b=0
   while time.monotonic()<until:
    for pos,n in enumerate(rng.permutation(names)):observe(n,'conditioning',b,pos,1)
    b+=1
   for b in range(24):
    for pos,n in enumerate(rng.permutation(names)):observe(n,'test',b,pos,10)
    save_rows(q/'requests.csv.gz',rows)
   for n,js in jobs.items():
    for s,j in enumerate(js):checks.append(dict(case=case,page=page,policy=n,slot=s,when='after',**j.check()));j.close()
   write(out/'numerical.json',checks);write(q/'complete.json',dict(status='PASS',test_requests=24*10*len(names)));print(process,case,page,'PASS',flush=True)
  d.close()
 write(out/'complete.json',dict(status='PASS'))
if __name__=='__main__':run(Path(sys.argv[1]),int(sys.argv[2]))
