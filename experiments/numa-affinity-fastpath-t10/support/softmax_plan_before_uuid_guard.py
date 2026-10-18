"""Experimental plan. Explicit policy, fixed T10 contract; no full-model claim."""
from soft_runtime import *
from const_runtime import ConstJob
from types import SimpleNamespace
class TopologySoftmaxPlan:
 def __init__(self,x,policy='NATIVE',mailbox_page=None,backend='constant'):
  begin=time.perf_counter()
  if mailbox_page is None:mailbox_page=read(ROOT/'freeze/MAILBOX_CHOICE.json')['page']
  if backend not in ['constant','global']:raise ValueError('Unknown mapping storage')
  job_type=ConstJob if backend=='constant' else SoftJob
  if not x.is_cuda or x.dtype!=torch.float32 or x.ndim!=1 or not x.is_contiguous():raise ValueError('Expected contiguous CUDA FP32 vocabulary vector')
  if x.numel() not in [32768,65536,131072,262144]:raise ValueError('Unqualified vocabulary size')
  prop=torch.cuda.get_device_properties(x.device)
  if prop.name!='Tesla T10' or prop.multi_processor_count!=56 or (prop.major,prop.minor)!=(7,5):raise ValueError('This frozen empirical map is qualified only for the 56-SM Tesla T10')
  if policy not in ['NATIVE','IDENTITY','MINIMAX','RANDOM','WRONG_ADDRESS']:raise ValueError('Unsupported policy')
  if mailbox_page not in [0,17,257]:raise ValueError('Uncalibrated mailbox address')
  if x.device.index!=torch.cuda.current_device():raise ValueError('Select the input device before constructing a plan')
  storage=torch.zeros(4<<20,device=x.device,dtype=torch.uint8) if policy!='NATIVE' else torch.empty(1,device=x.device,dtype=torch.uint8)
  d=SimpleNamespace(V=x.numel(),x=[x],y=torch.empty_like(x),partial=torch.empty(112,device=x.device),storage=storage,trace=torch.zeros(112,device=x.device,dtype=torch.int32),maps={},host_maps={})
  start=(-d.storage.data_ptr())%(2<<20);d.flags=d.storage[start:start+(2<<20)] if policy!='NATIVE' else d.storage
  maps=read(ROOT/'freeze/SOFTMAX_MAPS.json')['maps'];target='MINIMAX' if policy=='WRONG_ADDRESS' else policy;page=[0,17,257][([0,17,257].index(mailbox_page)+1)%3] if policy=='WRONG_ADDRESS' else mailbox_page
  for name in set(['IDENTITY',policy])-{'NATIVE'}:
   lookup=target if name==policy else name;pos=page if name==policy else mailbox_page;m=next(m for m in maps if m['page']==pos and m['policy']==lookup)
   d.host_maps[mailbox_page,name]=(I*56)(*m['map'])
   if backend=='global':d.maps[mailbox_page,name]=torch.tensor(m['map'],device=x.device,dtype=torch.int32)
  torch.cuda.synchronize()
  if policy!='NATIVE':
   probe=job_type(d,0,policy,mailbox_page,True);probe.run();tr=d.trace.cpu().view(56,2).numpy();probe.close()
   if not (np.array_equal(np.sort(tr[:,0]),np.arange(56)) and np.array_equal(tr[:,0],tr[:,1])):raise RuntimeError('Unexpected SM roster; empirical mapping invalid')
  self.d=d;self.job=job_type(d,0,policy,mailbox_page);self.job.graph.replay();torch.cuda.synchronize();torch.testing.assert_close(d.y,torch.softmax(x,dim=0),atol=2e-8,rtol=3e-5)
  self.setup_ms=(time.perf_counter()-begin)*1000;self.policy=policy;self.mailbox_page=mailbox_page;self.backend=backend
 def run(self):
  """Enqueue on the current PyTorch stream and return device output.

  Update the same input buffer before calling. Use a separate plan/workspace
  for concurrent streams; this plan and its output are not reentrant.
  """
  if self.job is None:raise RuntimeError('Closed plan')
  self.job.graph.replay();return self.d.y
 def close(self):
  if self.job is not None:self.job.close();self.job=None
