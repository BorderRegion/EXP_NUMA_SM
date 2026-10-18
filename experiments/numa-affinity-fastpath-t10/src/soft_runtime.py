from runtime import *
soft=C.CDLL(str(ROOT/'build/softmax.so'));soft.sf_error.restype=C.c_char_p;soft.sf_launch.argtypes=[C.POINTER(P),C.POINTER(I),C.c_ulonglong]
class SoftData:
 def __init__(self,V,seed,ring=4):
  self.V=V;self.seed=seed;g=torch.Generator().manual_seed(seed);self.x=[(torch.randn(V,generator=g)*3).cuda() for _ in range(ring)];self.y=torch.empty_like(self.x[0]);self.partial=torch.empty(112,device='cuda');self.storage=torch.zeros(4<<20,device='cuda',dtype=torch.uint8);start=(-self.storage.data_ptr())%(2<<20);self.flags=self.storage[start:start+(2<<20)];assert self.flags.data_ptr()%(2<<20)==0
  self.trace=torch.zeros(112,device='cuda',dtype=torch.int32);self.ref=[torch.softmax(x.cpu().double(),dim=0) for x in self.x];self.maps={};self.meta=dict(seed=seed,V=V,logits_sha256=[tensor_sha(x) for x in self.x],flags_va=self.flags.data_ptr(),x_va=[x.data_ptr() for x in self.x]);self.map_ms={}
  source=read(ROOT/'freeze/SOFTMAX_MAPS.json')['maps'] if (ROOT/'freeze/SOFTMAX_MAPS.json').exists() else [dict(page=p,policy='IDENTITY',map=(np.arange(56)//2).tolist()) for p in [0,17,257]]
  source=list(source)
  if any(m['policy']=='MINIMAX' for m in source):
   for i,page in enumerate([0,17,257]):
    m=next(x for x in source if x['page']==[0,17,257][(i+1)%3] and x['policy']=='MINIMAX');source.append(dict(page=page,policy='WRONG_ADDRESS',map=m['map']))
  for m in source:
   t=time.perf_counter();self.maps[m['page'],m['policy']]=torch.tensor(m['map'],dtype=torch.int32,device='cuda');torch.cuda.synchronize();self.map_ms[str((m['page'],m['policy']))]=(time.perf_counter()-t)*1000
  self.meta['map_upload_ms']=self.map_ms
 def check(self,slot):
  y=self.y.cpu().double();ref=self.ref[slot];delta=(y-ref).abs();scaled=float((delta/(2e-8+3e-5*ref.abs())).max());rel=float(delta.norm()/ref.norm());mass=float(y.sum());assert bool(torch.isfinite(y).all()) and scaled<1 and rel<1e-5 and abs(mass-1)<1e-5,(scaled,rel,mass)
  ctrl=self.flags.view(torch.int32)[400*1024:400*1024+6].cpu().numpy();assert ctrl[2]==0,ctrl
  return dict(status='PASS',relative_l2=rel,max_scaled_error=scaled,sum=mass,output_sha256=tensor_sha(self.y))
 def close(self):self.__dict__.clear();gc.collect();torch.cuda.empty_cache()
class SoftJob(Job):
 def __init__(self,d,slot,policy,page=0,trace=False):
  self.sfpolicy=policy;self.page=page;self.flagtrace=trace
  mapping=d.maps[page,policy] if policy not in ['TORCH','NATIVE'] else d.maps[page,'IDENTITY']
  self.a=(P*6)(d.x[slot].data_ptr(),d.y.data_ptr(),d.flags.data_ptr(),mapping.data_ptr(),d.trace.data_ptr(),d.partial.data_ptr());self.c=(I*4)(d.V,int(policy!='NATIVE'),page,int(trace));super().__init__(d,slot,'SOFTMAX')
 def op(self):
  if self.sfpolicy=='TORCH':torch.softmax(self.d.x[self.slot],dim=0,out=self.d.y)
  else:
   rc=soft.sf_launch(self.a,self.c,torch.cuda.current_stream().cuda_stream)
   if rc:raise RuntimeError(soft.sf_error().decode())
  self.state['out']=self.d.y
 def check(self):self.run();return self.d.check(self.slot)
