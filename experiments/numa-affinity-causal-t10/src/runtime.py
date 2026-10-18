from common import *
import ctypes as C,time,gc,gzip,csv
import numpy as np,torch
torch.set_num_threads(2)
P=C.c_void_p;I=C.c_int;DP=C.POINTER(C.c_double)
lib=C.CDLL(str(ROOT/'build/baseline/vector.so'));lib.ll_error.restype=C.c_char_p;lib.ll_timed.argtypes=[P];lib.ll_timed.restype=P;lib.ll_repeat.argtypes=[P,I,DP];lib.ll_drop.argtypes=[P];lib.ll_dag.argtypes=[P];lib.ll_dag.restype=C.c_char_p
libs={n:C.CDLL(str(ROOT/'build'/f'{n}.so')) for n in ['causal','softmax_const']}
for l in libs.values():l.sf_error.restype=C.c_char_p;l.sf_launch.argtypes=[C.POINTER(P),C.POINTER(I),C.c_ulonglong]
copy=C.CDLL(str(ROOT/'build/refresh.so'));copy.copy_launch.argtypes=[P,P,I,C.c_ulonglong]
VARIANTS={'OLD':1,'BAL':2,'FIX':3,'BOTH':4}
SCOPES=read(ROOT/'freeze/PROTOCOL.json')['scopes']
def tensor_sha(x):return hashlib.sha256(x.detach().cpu().contiguous().numpy().tobytes()).hexdigest()
def save_rows(p,rows):
 with gzip.open(p,'wt',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
class Data:
 def __init__(self,V,seed,ring=4):
  self.V=V;g=torch.Generator().manual_seed(seed);self.source=[(torch.randn(V,generator=g)*3).cuda() for _ in range(ring)];self.x=[x.clone() for x in self.source];self.y=torch.empty_like(self.x[0]);self.partial=torch.empty(112,device='cuda');self.storage=torch.zeros(4<<20,device='cuda',dtype=torch.uint8);start=(-self.storage.data_ptr())%(2<<20);self.flags=self.storage[start:start+(2<<20)];self.trace=torch.zeros(112,device='cuda',dtype=torch.int32);self.prof=torch.zeros((56,10),device='cuda',dtype=torch.int64)
  self.refs=[torch.softmax(x.cpu().double(),dim=0) for x in self.source];self.maps={(m['page'],m['policy']):(I*56)(*m['map']) for m in read(ROOT/'freeze/MAPS.json')['maps']};torch.cuda.synchronize()
  self.meta=dict(V=V,seed=seed,input_hashes=[tensor_sha(x) for x in self.source],flags_va=self.flags.data_ptr(),x_va=[x.data_ptr() for x in self.x],source_va=[x.data_ptr() for x in self.source]);assert self.flags.data_ptr()%(2<<20)==0
 def check(self,slot,native=False):
  y=self.y.cpu().double();ref=self.refs[slot];delta=(y-ref).abs();scaled=float((delta/(2e-8+3e-5*ref.abs())).max());rel=float(delta.norm()/ref.norm());mass=float(y.sum());assert bool(torch.isfinite(y).all()) and scaled<1 and rel<1e-5 and abs(mass-1)<1e-5,(scaled,rel,mass)
  ctrl=self.flags.view(torch.int32)[400*1024:400*1024+6].cpu().numpy();assert native or ctrl[2]==0,ctrl
  return dict(status='PASS',relative_l2=rel,max_scaled_error=scaled,sum=mass,output_sha256=tensor_sha(self.y))
 def close(self):self.__dict__.clear();gc.collect();torch.cuda.empty_cache()
class Job:
 def __init__(self,d,slot,variant,policy,page=17,scope='ready',trace=False):
  self.d=d;self.slot=slot;self.variant=variant;self.policy=policy;self.scope=scope;self.batch=SCOPES[scope]['batch'];self.fresh=SCOPES[scope]['fresh'];self.ptr=None;self.graph=None
  old=policy.startswith('BASE_');self.l=libs['softmax_const' if old else 'causal'];pol=policy[5:] if old else policy;self.mapping=d.maps[page,'IDENTITY' if pol=='NATIVE' else pol]
  self.a=(P*7)(d.x[slot].data_ptr(),d.y.data_ptr(),d.flags.data_ptr(),C.addressof(self.mapping),d.trace.data_ptr(),d.partial.data_ptr(),d.prof.data_ptr());self.c=(I*4)(d.V,0 if pol=='NATIVE' else 1 if old else VARIANTS[variant],page,int(trace))
  t=time.perf_counter()
  for _ in range(2):self.op()
  torch.cuda.synchronize();self.graph=torch.cuda.CUDAGraph(keep_graph=True)
  with torch.cuda.graph(self.graph):
   for _ in range(self.batch):self.op()
  raw=self.graph.raw_cuda_graph();self.ptr=lib.ll_timed(raw);assert self.ptr,lib.ll_error();self.dag=json.loads(lib.ll_dag(raw));self.setup_ms=(time.perf_counter()-t)*1000
 def op(self):
  st=torch.cuda.current_stream().cuda_stream
  if self.fresh:assert copy.copy_launch(self.d.source[self.slot].data_ptr(),self.d.x[self.slot].data_ptr(),self.d.V,st)==0
  if self.l.sf_launch(self.a,self.c,st):raise RuntimeError(self.l.sf_error().decode())
 def run(self,n=1):
  a=(C.c_double*(n*2))();rc=lib.ll_repeat(self.ptr,n,a);assert rc==0,lib.ll_error();return np.ctypeslib.as_array(a).copy().reshape(n,2)
 def check(self):
  torch.cuda.synchronize();self.run();return self.d.check(self.slot,self.policy=='NATIVE')
 def close(self):
  if self.ptr:lib.ll_drop(self.ptr);self.ptr=None
  self.graph=None
