from common import *
import ctypes as C,time,math,gc,gzip,csv
import numpy as np,torch
from torch.nn.attention import sdpa_kernel,SDPBackend
import torch.nn.functional as F
torch.set_num_threads(2);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cuda.matmul.allow_fp16_reduced_precision_reduction=False
lib=C.CDLL(str(ROOT/'build/attention.so'));P=C.c_void_p;I=C.c_int;DP=C.POINTER(C.c_double)
lib.ll_error.restype=C.c_char_p;lib.ll_launch.argtypes=[C.POINTER(P),C.POINTER(I),C.c_ulonglong];lib.ll_timed.argtypes=[P];lib.ll_timed.restype=P;lib.ll_repeat.argtypes=[P,I,DP];lib.ll_drop.argtypes=[P];lib.ll_dag.argtypes=[P];lib.ll_dag.restype=C.c_char_p
def check(x):
 if x:raise RuntimeError(lib.ll_error().decode())
def tensor_sha(x):return hashlib.sha256(x.detach().cpu().contiguous().numpy().tobytes()).hexdigest()
class Data:
 def __init__(self,c,seed,offset=0,ring=4):
  self.c=c;self.seed=seed;self.B=c['B'];self.H=c['H'];self.HK=c['HK'];self.D=c['D'];self.L=c['L'];self.G=self.H//self.HK;self.NP=(self.L+15)//16;self.capacity=self.NP*16;self.ring=ring;t=time.perf_counter()
  assert self.G in [1,4,8] and self.D in [128,256]
  n=self.B*self.NP*self.HK*16*self.D
  self.alloc=[]
  def cache():
   base=torch.empty(n+262144//2+offset//2,device='cuda',dtype=torch.float16);self.alloc.append(base);align=(-base.data_ptr())%262144;return base[(align+offset)//2:(align+offset)//2+n].view(self.B*self.NP,self.HK,16,self.D)
  self.k=cache();self.v=cache();gen=torch.Generator(device='cpu').manual_seed(seed)
  hk=(torch.rand(self.k.shape,generator=gen)*2-1).half();hv=(torch.rand(self.v.shape,generator=gen)*2-1).half();self.k.copy_(hk);self.v.copy_(hv)
  self.q=[(torch.randn((self.B,self.H,self.D),generator=gen)*.7).half().cuda() for _ in range(ring)]
  perm=np.random.default_rng(seed+19).permutation(self.B*self.NP).reshape(self.B,self.NP).astype(np.int32);self.table=torch.tensor(perm,device='cuda');self.length=torch.tensor(c.get('lengths',[self.L]*self.B),dtype=torch.int32,device='cuda')
  self.counter=torch.zeros(self.B*self.HK*3,dtype=torch.int32,device='cuda');self.partial=torch.empty(self.B*self.HK*16*self.G*(self.D+4),device='cuda',dtype=torch.float32);self.out=torch.empty((self.B,self.H,self.D),device='cuda',dtype=torch.float16)
  self.trace=torch.zeros(self.B*self.HK*self.NP*5,device='cuda',dtype=torch.int32);self.refs={};self.fp64={}
  self.table_long=self.table.long().reshape(-1);self.ideal_k,self.ideal_v=self.gather();self.mask=(torch.arange(self.capacity,device='cuda')[None,:]<self.length[:,None]).view(self.B,1,1,self.capacity)
  self.meta=dict(seed=seed,offset=offset,k_va=self.k.data_ptr(),v_va=self.v.data_ptr(),k_sha256=tensor_sha(hk),v_sha256=tensor_sha(hv),q_sha256=[tensor_sha(q) for q in self.q],page_table=perm.tolist(),lengths=c.get('lengths',[self.L]*self.B),source=c.get('source','QUALIFICATION'))
  self.lists={};self.labels={}
  for shuffled in [False,True]:
   encoded=[];labels=[]
   for b in range(self.B):
    for h in range(self.HK):
     a=np.array([(((self.k.data_ptr()+(int(p)*self.HK+h)*16*self.D*2)>>12)&0x33).bit_count()%2 for p in perm[b]],np.int32)
     if shuffled:a=a[np.random.default_rng(seed+500+b*self.HK+h).permutation(self.NP)]
     z=np.flatnonzero(a==0);o=np.flatnonzero(a==1);encoded.append(np.concatenate(([len(z),len(o)],z,o)));labels.append(a.tolist())
   key='shuffle' if shuffled else 'plain';self.lists[key]=torch.tensor(np.array(encoded),dtype=torch.int32,device='cuda');self.labels[key]=labels
  self.meta['classes']=self.labels;self.meta['kv_base_class_aligned']=((self.k.data_ptr()>>12)&0x33)==((self.v.data_ptr()>>12)&0x33)
  self.meta['per_task_K_bytes']=16*self.D*2;self.meta['address_class_scope']='first 4KiB of task; D256 task spans 8KiB, so class may mix within task'
  torch.cuda.synchronize();self.init_ms=(time.perf_counter()-t)*1000;self.headroom()
 def headroom(self):
  free,total=torch.cuda.mem_get_info();assert free>=max(2<<30,total*.15),(free,total)
 def gather(self):
  def one(x):return x.index_select(0,self.table_long).view(self.B,self.NP,self.HK,16,self.D).permute(0,2,1,3,4).contiguous().view(self.B,self.HK,self.capacity,self.D)
  return one(self.k),one(self.v)
 def reference(self,slot):
  if slot not in self.refs:
   q=self.q[slot].float().view(self.B*self.HK,self.G,self.D);k=self.ideal_k.float().view(self.B*self.HK,self.capacity,self.D);v=self.ideal_v.float().view_as(k)
   logits=torch.bmm(q,k.transpose(1,2))/math.sqrt(self.D);logits=logits.view(self.B,self.HK,self.G,self.capacity).masked_fill(~self.mask,-float('inf'));p=logits.softmax(-1).reshape(self.B*self.HK,self.G,self.capacity);out=torch.bmm(p,v).view(self.B,self.H,self.D);self.refs[slot]=out.cpu()
   q=self.q[slot][0,0].cpu().double();k=self.ideal_k[0,0,:int(self.length[0])].cpu().double();v=self.ideal_v[0,0,:int(self.length[0])].cpu().double();self.fp64[slot]=torch.softmax(k@q/math.sqrt(self.D),dim=0)@v
  return self.refs[slot]
 def check(self,out,slot):
  ref=self.reference(slot).double();o=out.detach().cpu().double();dif=(o-ref).abs();scaled=float((dif/(3e-4+3e-3*ref.abs())).max());rel=float(torch.linalg.vector_norm(dif)/torch.linalg.vector_norm(ref).clamp_min(1e-20));rr=self.fp64[slot];err64=float(((o[0,0]-rr).abs()/(3e-4+3e-3*rr.abs())).max())
  assert bool(torch.isfinite(o).all()) and scaled<=1 and rel<=2e-3 and err64<=1,(scaled,rel,err64)
  return dict(status='PASS',relative_frobenius=rel,max_scaled_error=scaled,fp64_first_head_scaled_error=err64,output_sha256=tensor_sha(out))
 def close(self):
  self.__dict__.clear();gc.collect();torch.cuda.empty_cache()
class Job:
 def __init__(self,d,slot,policy,W=4,fused=0,mode=0,trace=False):
  self.d=d;self.slot=slot;self.policy=policy;self.W=W;self.fused=fused;self.mode=mode;self.ptr=None;self.state={};self.trace_enabled=trace
  if policy=='CUSTOM':
   ls=d.lists['shuffle' if mode==4 else 'plain'];args=[d.q[slot],d.k,d.v,d.table,d.length,ls,d.counter,d.partial,d.out,d.trace if trace else None];self.args=(P*10)(*[x.data_ptr() if x is not None else 0 for x in args]);self.cfg=(I*9)(d.D,d.G,d.B,d.HK,d.NP,W,mode,fused,int(trace))
  t=time.perf_counter()
  for _ in range(2):self.op()
  torch.cuda.synchronize();self.graph=torch.cuda.CUDAGraph(keep_graph=True)
  with torch.cuda.graph(self.graph):self.op()
  raw=self.graph.raw_cuda_graph();self.ptr=lib.ll_timed(raw)
  if not self.ptr:raise RuntimeError(lib.ll_error().decode())
  z=lib.ll_dag(raw)
  if not z:raise RuntimeError(lib.ll_error().decode())
  self.dag=json.loads(z);self.build_ms=(time.perf_counter()-t)*1000
 def op(self):
  d=self.d
  if self.policy=='CUSTOM':check(lib.ll_launch(self.args,self.cfg,torch.cuda.current_stream().cuda_stream));self.state['out']=d.out;return
  k,v=d.gather() if self.policy.endswith('PAGED') else (d.ideal_k,d.ideal_v)
  if self.policy.startswith('SDPA'):
   k=k.repeat_interleave(d.G,dim=1) if d.G!=1 else k;v=v.repeat_interleave(d.G,dim=1) if d.G!=1 else v
   with sdpa_kernel(SDPBackend.EFFICIENT_ATTENTION):self.state['out']=F.scaled_dot_product_attention(d.q[self.slot].unsqueeze(2),k,v,attn_mask=d.mask).squeeze(2)
  else:
   logits=torch.bmm(d.q[self.slot].view(d.B*d.HK,d.G,d.D),k.reshape(d.B*d.HK,d.capacity,d.D).transpose(1,2),out_dtype=torch.float32)/math.sqrt(d.D)
   logits=logits.view(d.B,d.HK,d.G,d.capacity).masked_fill(~d.mask,-float('inf'));prob=logits.softmax(-1).half().view(d.B*d.HK,d.G,d.capacity)
   self.state['out']=torch.bmm(prob,v.reshape(d.B*d.HK,d.capacity,d.D),out_dtype=torch.float32).half().view(d.B,d.H,d.D)
 def run(self,n=1):
  out=(C.c_double*(n*2))();check(lib.ll_repeat(self.ptr,n,out));return np.ctypeslib.as_array(out).copy().reshape(n,2)
 def check(self):self.run();r=self.d.check(self.state['out'],self.slot);assert not self.d.counter.count_nonzero().item();return r
 def close(self):
  if self.ptr:lib.ll_drop(self.ptr);self.ptr=None
  self.graph=None;self.state={}
def save_rows(path,rows):
 with gzip.open(path,'wt',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
