import ctypes as C,time,math,json,os
import numpy as np
import torch
from common import *
torch.set_num_threads(2);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cuda.matmul.allow_fp16_reduced_precision_reduction=False
BUILD=Path(os.environ.get('PC_BUILD',(ROOT/'BUILD.txt').read_text().strip()));lib=C.CDLL(str(BUILD/'backend.so'))
print('ACTUAL_BUILD_PATH',str(BUILD),flush=True)
P=C.c_void_p;I=C.c_int;DP=C.POINTER(C.c_double)
lib.pc_error.restype=C.c_char_p
if hasattr(lib,'pc_dag_json'):lib.pc_dag_json.argtypes=[P];lib.pc_dag_json.restype=C.c_char_p
lib.pc_create.argtypes=[C.c_char_p,I];lib.pc_create.restype=P
lib.pc_setup_costs.argtypes=[P,DP]
lib.pc_destroy.argtypes=[P];lib.pc_groups.argtypes=[P,C.POINTER(I)]
lib.pc_roster.argtypes=[P,I,P,C.POINTER(C.c_uint),I]
lib.pc_build.argtypes=[P,C.POINTER(I),C.POINTER(P),C.c_float,C.c_float];lib.pc_build.restype=P
lib.pc_drop.argtypes=[P];lib.pc_run.argtypes=[P,DP];lib.pc_batch.argtypes=[P,I,DP];lib.pc_nodes.argtypes=[P,C.POINTER(I)]
def check(code):
 if code:raise RuntimeError(lib.pc_error().decode())
class Engine:
 def __init__(self,mode=-1):
  torch.cuda.init();t=time.perf_counter();self.ptr=lib.pc_create(str(BUILD).encode(),mode)
  if not self.ptr:raise RuntimeError(lib.pc_error().decode())
  self.init_ms=(time.perf_counter()-t)*1000;a=(I*10)();check(lib.pc_groups(self.ptr,a));self.quad=list(a[:4]);self.halves=[list(a[4+2*i:6+2*i]) for i in range(3)]
  costs=(C.c_double*4)();check(lib.pc_setup_costs(self.ptr,costs));self.setup_costs=dict(driver_init_ms=costs[0],resource_enumeration_ms=costs[1],green_create_ms=costs[2],live_green_contexts=int(costs[3]))
  self.membership={};buf=torch.empty(512,device='cuda',dtype=torch.int32);host=(C.c_uint*512)()
  for g in sorted(set(x for x in self.quad+sum(self.halves,[]) if x>=0)):
   found=set()
   for _ in range(8):
    check(lib.pc_roster(self.ptr,g,buf.data_ptr(),host,512));found.update(host)
    if len(found)==(14 if g in self.quad else 28):break
   expected=14 if g in self.quad else 28
   if len(found)!=expected:raise RuntimeError(f'resource roster {g}: {len(found)}/{expected}')
   self.membership[g]=sorted(found)
  for hs in [x for x in self.halves if x[0]>=0]:assert len(set(self.membership[hs[0]])|set(self.membership[hs[1]]))==56 and not set(self.membership[hs[0]])&set(self.membership[hs[1]])
  self.roster_ms=(time.perf_counter()-t)*1000-self.init_ms
 def close(self):
  if self.ptr:check(lib.pc_destroy(self.ptr));self.ptr=None
class Data:
 def __init__(self,m,n,k,s=16,seed=1,ring=4,chain=False,deployment_workspace_words=None):
  self.m,self.n,self.k=m,n,k;self.seed=seed;self.ring=ring;self.chain=chain
  free,total=torch.cuda.mem_get_info();need=2*(ring*m*k+n*k)+4*(m*n*ring)+4*((m+127)//128*128)*((n+127)//128*128)*s*2+(128<<20)
  if deployment_workspace_words is not None:need=2*(ring*m*k+n*k)+4*m*n*2+4*deployment_workspace_words
  if chain:need+=2*n*k+2*m*n+4*m*k
  if free-need<max(2<<30,.15*total):raise MemoryError(f'headroom expected {free-need}')
  t=time.perf_counter();gen=torch.Generator(device='cpu').manual_seed(seed)
  self.ha=[((torch.rand((m,k),generator=gen)*2-1)/math.sqrt(k)).half() for _ in range(ring)]
  self.hb=(torch.rand((n,k),generator=gen)*2-1).half();self.a=[x.cuda() for x in self.ha];self.b=self.hb.cuda()
  self.d=torch.empty((m,n),device='cuda',dtype=torch.float32);self.c=torch.zeros_like(self.d)
  self.wsize=((m+127)//128*128)*((n+127)//128*128)*s
  self.w=torch.empty(self.wsize*2 if deployment_workspace_words is None else max(1,deployment_workspace_words),device='cuda',dtype=torch.float32)
  self.trace=torch.full(((max(4096,((m+31)//32)*((n+63)//64)*(s+64)*5) if deployment_workspace_words is None else 1),),-1,device='cuda',dtype=torch.int32)
  self.scratch=torch.arange((128<<20)//4 if deployment_workspace_words is None else 1,device='cuda',dtype=torch.int32);self.scratchout=torch.empty(256*128,device='cuda',dtype=torch.int32)
  self.act=self.b2=self.d2=None
  if chain:
   self.act=torch.empty((m,n),device='cuda',dtype=torch.float16);self.hb2=(torch.rand((k,n),generator=gen)*2-1).half()/math.sqrt(n);self.b2=self.hb2.cuda();self.d2=torch.empty((m,k),device='cuda',dtype=torch.float32)
  torch.cuda.synchronize();self.init_ms=(time.perf_counter()-t)*1000;self.allocated=torch.cuda.memory_allocated();self.free_after=torch.cuda.mem_get_info()[0];assert self.free_after>=max(2<<30,.15*total)
  self.refs={};self.fp64_refs={};self.chain_refs={};self._base_outputs={}
 def ref(self,slot):
  if slot not in self.refs:
   # Turing FP32 GEMM, reduced precision disabled, complete matrix reference.
   x=self.a[slot].float()@self.b.float().T
   self.refs[slot]=x.cpu();del x
  return self.refs[slot]
 def numerical(self,slot,alpha=1,beta=0):
  out=self.d.detach().cpu();ref=self.ref(slot)*alpha+self.c.cpu()*beta
  dif=(out.double()-ref.double()).abs();tol=1e-4+2e-3*ref.double().abs();scaled=float((dif/tol).max());rel=float(torch.linalg.vector_norm(dif)/torch.linalg.vector_norm(ref.double()).clamp_min(1e-30))
  full64=self.m*self.n<=65536 and self.m*self.n*self.k<=100000000
  ix=torch.arange(self.m) if full64 else torch.linspace(0,self.m-1,min(32,self.m)).long();iy=torch.arange(self.n) if full64 else torch.linspace(0,self.n-1,min(32,self.n)).long()
  if slot not in self.fp64_refs:self.fp64_refs[slot]=self.ha[slot][ix].double()@self.hb[iy].double().T
  dr=self.fp64_refs[slot]*alpha+self.c.cpu()[ix][:,iy].double()*beta;dd=(out[ix][:,iy].double()-dr).abs();max64=float((dd/(1e-4+2e-3*dr.abs())).max())
  ok=bool(torch.isfinite(out).all()) and rel<=1e-3 and scaled<=1 and max64<=1
  if not ok:raise RuntimeError(f'NUMERICAL_ERROR rel={rel} scaled={scaled} fp64={max64}')
  result=dict(status='PASS',relative_frobenius=rel,max_scaled_error=scaled,fp64_subblock_max_scaled_error=max64,full_reference='FP32_TORCH_NO_REDUCED_ACCUMULATION',fp64_subblock=[len(ix),len(iy)],fp64_scope='FULL' if full64 else 'PREDECLARED_SUBBLOCK',output_sha256=sha_bytes(out))
  if self.chain:
   key=(slot,alpha,beta)
   if key not in self.chain_refs:self.chain_refs[key]=torch.nn.functional.silu(ref).half().float()@self.hb2.float().T
   ref2=self.chain_refs[key];o2=self.d2.cpu();err=(o2-ref2).double().abs();sc=float((err/(5e-4+3e-3*ref2.abs())).max());rr=float(torch.linalg.vector_norm(err)/torch.linalg.vector_norm(ref2.double()).clamp_min(1e-30));
   if rr>2e-3 or sc>1:raise RuntimeError(f'CHAIN_NUMERICAL_ERROR {rr} {sc}')
   result['chain']=dict(relative_frobenius=rr,max_scaled_error=sc,output_sha256=sha_bytes(o2))
  return result
 def close(self):
  self.a=[];self.b=self.d=self.c=self.w=self.trace=self.scratch=self.scratchout=self.act=self.b2=self.d2=None;self.refs={};torch.cuda.empty_cache()
def sha_bytes(x):return __import__('hashlib').sha256(x.contiguous().numpy().tobytes()).hexdigest()
class Job:
 def __init__(self,e,d,recipe=0,s=2,kind=0,slab=0,pg=None,cg=None,slot=0,wslot=0,submit_reverse=0,task_reverse=0,scratch=0,diag=0,generation=1,f1=0,stages=0,alpha=1,beta=0):
  self.e=e;self.d=d;self.slot=slot;self.recipe=recipe;self.s=s;self.diag=diag;self.generation=generation;self.kind=kind;self.pg=pg;self.cg=cg;self.alpha=alpha;self.beta=beta
  if pg is None:pg=[-1,-1]
  if cg is None:cg=pg
  self.cfg=[d.m,d.n,d.k,s,recipe,kind,slab,*pg,*cg,submit_reverse,task_reverse,scratch,diag,generation,f1,int(d.chain),d.k,stages];assert len(self.cfg)==20
  pts=[d.a[slot].data_ptr(),d.b.data_ptr(),d.w.data_ptr()+wslot*d.wsize*4,d.d.data_ptr(),d.c.data_ptr(),d.trace.data_ptr(),d.scratch.data_ptr(),d.scratchout.data_ptr(),d.act.data_ptr() if d.chain else 0,d.b2.data_ptr() if d.chain else 0,d.d2.data_ptr() if d.chain else 0]
  t=time.perf_counter();self.ptr=lib.pc_build(e.ptr,(I*20)(*self.cfg),(P*11)(*pts),alpha,beta)
  if not self.ptr:raise RuntimeError(lib.pc_error().decode())
  self.build_ms=(time.perf_counter()-t)*1000;nodes=(I*2)();check(lib.pc_nodes(self.ptr,nodes));self.nodes=list(nodes)
  self.dag=json.loads(lib.pc_dag_json(self.ptr).decode()) if hasattr(lib,'pc_dag_json') else dict(status='LEGACY_FROZEN_MATRIX_RUNTIME_COUNTS_ONLY',kernel_count=self.nodes[0],body_node_count=self.nodes[1])
 def run(self):
  out=(C.c_double*5)();check(lib.pc_run(self.ptr,out));return list(out)
 def batch(self,n):
  out=(C.c_double*2)();check(lib.pc_batch(self.ptr,n,out));return list(out)
 def placement(self):
  if not self.diag:raise ValueError('only DIAG1')
  self.d.trace.fill_(-1);torch.cuda.synchronize();self.run();x=self.d.trace.cpu().numpy().reshape(-1)[:(self.d.trace.numel()//5)*5].reshape(-1,5);x=x[x[:,4]==self.generation]
  bm,bn=[(32,64),(64,64),(64,128),(128,128)][self.recipe];nt=((self.d.m+bm-1)//bm)*((self.d.n+bn-1)//bn);rows=(bm+3)//4;cols=(bn+127)//128
  p=x[x[:,2]>=0];r=x[x[:,2]==-1]
  # R diagnostics include boundary rows that have no valid elements, harmless qualification writes.
  if len(p)!=nt*self.s:raise RuntimeError(f'P coverage {len(p)} != {nt*self.s}')
  expected_r=nt*rows*cols if os.environ.get('PC_BUILD') else ((self.d.m+3)//4)*((self.d.n+bn-1)//bn)*cols
  if len(r)!=expected_r:raise RuntimeError(f'R coverage {len(r)} != {expected_r}')
  for role,records,groups in [('P',p,self.pg),('R',r,self.cg or self.pg)]:
   if self.kind==1 and not os.environ.get('PC_BUILD') and not np.array_equal(records[:,1]%2,records[:,3]):raise RuntimeError('logical owner mismatch')
   for owner in range(2 if self.kind==1 else 1):
    z=records[records[:,3]==owner];actual=set(map(int,z[:,0]));expected=set(self.e.membership[groups[owner]]) if groups[owner]>=0 else set(range(10000))
    if not actual<=expected:raise RuntimeError(f'{role} placement {actual-expected}')
  self.d.numerical(self.slot,self.alpha,self.beta)
  return dict(status='PASS',P_records=len(p),R_records=len(r),P_actual_sms=sorted(set(map(int,p[:,0]))),R_actual_sms=sorted(set(map(int,r[:,0]))),generation=self.generation,trace=x.tolist())
 def close(self):
  if self.ptr:check(lib.pc_drop(self.ptr));self.ptr=None
