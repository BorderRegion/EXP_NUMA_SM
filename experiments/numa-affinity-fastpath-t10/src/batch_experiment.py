from const_runtime import *
import sys
class BatchJob(ConstJob):
 def __init__(self,*args,**kwargs):
  super().__init__(*args,**kwargs);lib.ll_drop(self.ptr);self.ptr=None;self.graph=None;self.graph=torch.cuda.CUDAGraph(keep_graph=True)
  with torch.cuda.graph(self.graph):
   for i in range(32):self.op()
  self.ptr=lib.ll_timed(self.graph.raw_cuda_graph());assert self.ptr;self.dag=json.loads(lib.ll_dag(self.graph.raw_cuda_graph()))
def run(out,process):
 rng=np.random.default_rng(111000000+process);checks=[]
 for V in rng.permutation([32768,65536,131072,262144]):
  V=int(V);d=ConstData(V,111000000+process*100000+V);case='VOCAB_'+str(V)
  for page in rng.permutation([0,17,257]):
   page=int(page);q=out/case/f'offset_{page}';q.mkdir(parents=True);names=['MINIMAX','IDENTITY','WORST','WRONG_ADDRESS','NATIVE']+[f'RND{i:02d}' for i in range(12)];jobs={n:[BatchJob(d,s,n,page) for s in range(4)] for n in names}
   write(q/'mapping.json',d.meta);write(q/'configs.json',dict(page=page,batch_size=32,policies=names));write(q/'graphs.json',{n:js[0].dag for n,js in jobs.items()});rows=[]
   for n,js in jobs.items():
    for s,j in enumerate(js):checks.append(dict(case=case,page=page,policy=n,slot=s,when='before',**j.check()))
   def observe(name,stage,b,pos,n):
    begin=time.monotonic_ns();vv=jobs[name][b%4].run(n);end=time.monotonic_ns()
    for i,v in enumerate(vv):rows.append(dict(case=case,offset=page,phase=stage,block=b,position=pos,label=name,slot=b%4,request=i,batch_size=32,gpu_us=v[0],host_us=v[1],begin_ns=begin,end_ns=end))
   until=time.monotonic()+.15;b=0
   while time.monotonic()<until:
    for pos,n in enumerate(rng.permutation(names)):observe(n,'conditioning',b,pos,1)
    b+=1
   for b in range(8):
    for pos,n in enumerate(rng.permutation(names)):observe(n,'test',b,pos,6)
    save_rows(q/'requests.csv.gz',rows)
   for n,js in jobs.items():
    for s,j in enumerate(js):checks.append(dict(case=case,page=page,policy=n,slot=s,when='after',**j.check()));j.close()
   write(out/'numerical.json',checks);write(q/'complete.json',dict(status='PASS',timed_batches=8*6*len(names),operator_requests=8*6*len(names)*32));print(process,case,page,'PASS',flush=True)
  d.close()
 write(out/'complete.json',dict(status='PASS'))
if __name__=='__main__':run(Path(sys.argv[1]),int(sys.argv[2]))
