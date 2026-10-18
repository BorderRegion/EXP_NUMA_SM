"""Measured-shape dispatch for paged decode, optional KV append.
Use PagedDecodePlan's tensor/layout/concurrency contract. Routing is selected
once on construction. No CPU address fitting, queues or allocations in launch.
The five fused-append recommendations are post-confirmation decisions; their
benchmark estimates are not a second independent deployment holdout.
"""
from kernel_api import PagedDecodePlan,library,P,I,C,torch
from common import *
_core=None
def original_library():
 global _core
 if _core is None:
  _core=C.CDLL(str(ROOT/'build/attention.so'));_core.ll_error.restype=C.c_char_p;_core.ll_launch.argtypes=[C.POINTER(P),C.POINTER(I),C.c_ulonglong]
 return _core
class OptimizedPagedDecode(PagedDecodePlan):
 def __init__(self,*args,**kwargs):
  super().__init__(*args,**kwargs);b,h,d=self.q.shape;hk=self.k.shape[1];npages=self.table.shape[1]
  choices=read(ROOT/'freeze/DEPLOYMENT_POLICY.json')['cases'];self.case_id=None;self.recommended='legacy_separate'
  for cid,x in choices.items():
   if x['shape']==[b,h,hk,d,npages*16]:self.case_id=cid;self.recommended=x['append'];break
  if self.new_k is None:self.recommended='none'
  original_library()
 def launch(self,append='auto'):
  mode=self.recommended if append=='auto' else append
  if mode=='fused':return super().launch('fused')
  if mode=='modified_separate':return super().launch('separate')
  if mode not in ['separate','legacy_separate','none']:raise ValueError('append must be auto, fused, separate, none, or modified_separate')
  stream=torch.cuda.current_stream(self.q.device).cuda_stream
  if mode!='none':
   if self.new_k is None:raise ValueError('Append inputs were not supplied')
   z=library();rc=z.ll_append(self.yes,self.cfg,stream)
   if rc:raise RuntimeError(z.ll_error().decode())
  z=original_library();rc=z.ll_launch(self.no,self.cfg,stream)
  if rc:raise RuntimeError(z.ll_error().decode())
  return self.output
