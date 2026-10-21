from gqa_data import *
libraries={}
for name,path in [('N19',REPO/'numa-locality-scheduling-t10/build/vector.so'),('N19_APPEND',REPO/'numa-locality-scheduling-t10/build/vector_append.so'),('E56',ROOT/'build/gqa.so'),('E56_APPEND',ROOT/'build/gqa_append.so')]:
 z1=C.CDLL(str(path));z1.ll_error.restype=C.c_char_p;z1.ll_launch.argtypes=[C.POINTER(P),C.POINTER(I),C.c_ulonglong];libraries[name]=z1
class GQAData(Data):
 def __init__(self,case,seed,offset):
  super().__init__(case,seed,offset,4)
  self.initial_k=self.k.clone();self.initial_v=self.v.clone();self.new_k=[];self.new_v=[];self.numerical_refs={}
  gen=torch.Generator(device='cpu').manual_seed(seed+830001)
  for slot in range(4):
   self.new_k.append((torch.randn((self.B,self.HK,self.D),generator=gen)*.7).half().cuda())
   self.new_v.append((torch.randn((self.B,self.HK,self.D),generator=gen)*.7).half().cuda())
  for append in [False,True]:
   self.refs={};self.fp64={}
   for slot in range(4):
    if append:
     for b,pos in enumerate(self.meta['lengths']):
      page=self.meta['page_table'][b][(pos-1)//16];self.k[page,:,(pos-1)%16,:]=self.new_k[slot][b];self.v[page,:,(pos-1)%16,:]=self.new_v[slot][b]
     self.ideal_k,self.ideal_v=self.gather()
    self.reference(slot)
   self.numerical_refs[append]=(dict(self.refs),dict(self.fp64))
  self.reset();self.meta['new_k_sha256']=[tensor_sha(x) for x in self.new_k];self.meta['new_v_sha256']=[tensor_sha(x) for x in self.new_v]
 def reset(self):
  ck(z.gc_current(0));self.k.copy_(self.initial_k);self.v.copy_(self.initial_v);self.counter.zero_();torch.cuda.synchronize()
 def check_mode(self,append,slot,raw_reference=None):
  self.refs,self.fp64=self.numerical_refs[append];res=self.check(self.out,slot);assert not self.counter.count_nonzero().item()
  expected_k=self.initial_k.clone();expected_v=self.initial_v.clone()
  if append:
   for b,pos in enumerate(self.meta['lengths']):
    page=self.meta['page_table'][b][(pos-1)//16];expected_k[page,:,(pos-1)%16,:]=self.new_k[slot][b];expected_v[page,:,(pos-1)%16,:]=self.new_v[slot][b]
  assert torch.equal(self.k,expected_k) and torch.equal(self.v,expected_v)
  res['non_target_cache_unchanged']=True
  if raw_reference is not None:res['same_input_N19_raw_bit_equal']=bool(torch.equal(self.out.cpu(),raw_reference))
  return res
class GQAJob:
 def __init__(self,d,append,backend,trace=False):
  self.d=d;self.append=append;self.backend=backend
  policy=read(RUN/'freeze/N19_DEPLOYMENT_POLICY.json')['cases'][d.c['id']]['append' if append else 'attention']
  old=read(RUN/'freeze/N19_LEGACY_SELECTION.json')['cases'][d.c['id']]
  self.fused=int(old['best_custom']=='FUSED');self.W=old['fused' if self.fused else 'direct'];self.mode=1 if policy=='VECTOR_BLIND' else 0
  self.policy=policy;self.z=libraries[backend+('_APPEND' if append else '')]
  self.args=[];self.cfg=(I*10)(d.D,d.G,d.B,d.HK,d.NP,self.W,self.mode,self.fused,int(trace),1)
  for slot in range(4):
   a=[d.q[slot],d.k,d.v,d.table,d.length,d.lists['plain'] if self.mode else None,d.counter,d.partial,d.out,d.trace if trace else None,d.new_k[slot],d.new_v[slot]]
   self.args.append((P*12)(*[v.data_ptr() if v is not None else 0 for v in a]))
 def op(self,slot):
  def launch(stream):
   rc=self.z.ll_launch(self.args[slot],self.cfg,stream)
   if rc:raise RuntimeError(self.z.ll_error().decode())
  return launch
