from fresh_experiment import FreshJob,copy
from soft_runtime import *
const=C.CDLL(str(ROOT/'build/softmax_const.so'));const.sf_error.restype=C.c_char_p;const.sf_launch.argtypes=[C.POINTER(P),C.POINTER(I),C.c_ulonglong]
class ConstData(SoftData):
 def __init__(self,*args,**kw):
  super().__init__(*args,**kw);self.source=[x.clone() for x in self.x]
  for m in read(ROOT/'freeze/PANEL_PROTOCOL.json')['maps']:self.maps[m['page'],m['policy']]=torch.tensor(m['map'],device='cuda',dtype=torch.int32)
  self.host_maps={k:(I*56)(*v.cpu().tolist()) for k,v in self.maps.items()};torch.cuda.synchronize()
class ConstJob(SoftJob):
 def __init__(self,d,slot,policy,page=0,trace=False,fresh=False):
  self.sfpolicy=policy;self.page=page;self.flagtrace=trace;self.fresh=fresh;mapping=d.host_maps[page,policy if policy!='NATIVE' else 'IDENTITY'];self.map_keepalive=mapping
  self.a=(P*6)(d.x[slot].data_ptr(),d.y.data_ptr(),d.flags.data_ptr(),C.addressof(mapping),d.trace.data_ptr(),d.partial.data_ptr());self.c=(I*4)(d.V,int(policy!='NATIVE'),page,int(trace));Job.__init__(self,d,slot,'CONST_SOFTMAX')
 def op(self):
  if self.fresh:
   rc=copy.copy_launch(self.d.source[self.slot].data_ptr(),self.d.x[self.slot].data_ptr(),self.d.V,torch.cuda.current_stream().cuda_stream)
   if rc:raise RuntimeError('copy failed')
  rc=const.sf_launch(self.a,self.c,torch.cuda.current_stream().cuda_stream)
  if rc:raise RuntimeError(const.sf_error().decode())
  self.state['out']=self.d.y
