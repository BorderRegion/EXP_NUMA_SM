from runtime import *
from kernel_api import PagedDecodePlan
import sys
class Captured:
 def __init__(self,d,slot,nk,nv,mode):
  self.d=d;self.slot=slot;self.mode=mode;self.plan=PagedDecodePlan(d.q[slot],d.k,d.v,d.table,d.length,nk,nv);self.ptr=None
  for _ in range(2):self.plan.launch(mode)
  torch.cuda.synchronize();self.graph=torch.cuda.CUDAGraph(keep_graph=True)
  with torch.cuda.graph(self.graph):self.plan.launch(mode)
  self.ptr=lib.ll_timed(self.graph.raw_cuda_graph());assert self.ptr,lib.ll_error().decode();self.dag=json.loads(lib.ll_dag(self.graph.raw_cuda_graph()))
 def run(self,n=1):
  a=(C.c_double*(2*n))();check(lib.ll_repeat(self.ptr,n,a));return np.ctypeslib.as_array(a).copy().reshape(n,2)
 def check(self):
  self.run();d=self.d;d.ideal_k,d.ideal_v=d.gather();d.refs={};d.fp64={};r=d.check(self.plan.output,self.slot);assert not self.plan.counter.count_nonzero().item()
  if self.mode!='none':
   for b in range(d.B):
    pos=int(d.length[b])-1;page=int(d.table[b,pos//16]);assert torch.equal(d.k[page,:,pos%16],self.plan.new_k[b]);assert torch.equal(d.v[page,:,pos%16],self.plan.new_v[b])
  return r
 def close(self):
  if self.ptr:lib.ll_drop(self.ptr);self.ptr=None
  self.graph=None;self.plan=None

def run(out,proc):
 prot=read(ROOT/'freeze/PROTOCOL.json');rng=np.random.default_rng(6600000+proc);nums=[]
 for ci in rng.permutation(len(prot['cases'])):
  c=prot['cases'][ci];cid=c['id']
  for off in [0,69632]:
   q=out/cid/f'offset_{off}';q.mkdir(parents=True);d=Data(c,5500000+proc*10000+int(ci)*101,off);gen=torch.Generator(device='cpu').manual_seed(d.seed+15)
   nk=[(torch.rand((d.B,d.HK,d.D),generator=gen)*2-1).half().cuda() for _ in range(4)];nv=[(torch.rand((d.B,d.HK,d.D),generator=gen)*2-1).half().cuda() for _ in range(4)]
   t=time.perf_counter();jobs={p:[Captured(d,s,nk[s],nv[s],mode) for s in range(4)] for p,mode in [('SEPARATE','separate'),('FUSED_APPEND','fused'),('ATTENTION_ONLY','none')]};build_ms=(time.perf_counter()-t)*1000
   write(q/'metadata.json',dict(**d.meta,new_k_hashes=[tensor_sha(x) for x in nk],new_v_hashes=[tensor_sha(x) for x in nv],build_ms=build_ms,workers=jobs['SEPARATE'][0].plan.workers,fused_finish=jobs['SEPARATE'][0].plan.fused_finish));write(q/'graphs.json',{p:[j.dag for j in js] for p,js in jobs.items()})
   for p,js in jobs.items():
    for slot,j in enumerate(js):nums.append(dict(case=cid,offset=off,policy=p,slot=slot,phase='before',**j.check()))
   rows=[]
   def observe(label,phase,b,pos,n):
    name='SEPARATE' if label.startswith('ANCHOR_') else label;start=time.monotonic_ns();vv=jobs[name][b%4].run(n);end=time.monotonic_ns()
    for i,v in enumerate(vv):rows.append(dict(case=cid,offset=off,phase=phase,block=b,position=pos,label=label,slot=b%4,request=i,gpu_us=v[0],host_us=v[1],begin_ns=start,end_ns=end))
   for b in range(8):
    # Prepare this slot's cache even before the attention-only lower bound.
    for pos,p in enumerate(['SEPARATE','FUSED_APPEND','ATTENTION_ONLY']):observe(p,'conditioning',b,pos,4)
   for b in range(30):
    order=['ANCHOR_A']+rng.permutation(list(jobs)).tolist()+['ANCHOR_B']
    for pos,p in enumerate(order):observe(p,'test',b,pos,8)
    save_rows(q/'requests.csv.gz',rows)
   for p,js in jobs.items():
    for slot,j in enumerate(js):nums.append(dict(case=cid,offset=off,policy=p,slot=slot,phase='after',**j.check()));j.close()
   write(out/'numerical.json',nums);write(q/'complete.json',dict(status='PASS',selection_sha256=sha(ROOT/'freeze/SELECTION.json'),protocol_sha256=sha(ROOT/'freeze/APPEND_PROTOCOL.json')));d.close();print('APPEND',proc,cid,off,'PASS',flush=True)
 write(out/'complete.json',dict(status='PASS',checks=len(nums)));print('APPEND_CONFIRMATION_PASS')
if __name__=='__main__':run(Path(sys.argv[1]),int(sys.argv[2]))
