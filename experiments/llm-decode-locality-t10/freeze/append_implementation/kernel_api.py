"""Paged GQA decode kernel, with optional fused KV append.
FP16 Q/K/V/output, FP32 attention state. Cache: [physical_pages, kv_heads,16,D].
Live length is inclusive of the appended token. Terminal writable pages MUST be
private to each sequence (normal copy-on-write paged-cache contract). Q, K/V,
lengths, page table and append values stay alive for the plan lifetime.
launch() uses the current PyTorch stream, allocates nothing, and may be captured
in CUDA Graphs. One private plan/workspace per concurrent invocation.
"""
from common import *
import ctypes as C
import torch
P=C.c_void_p;I=C.c_int
_lib=None
def library():
 global _lib
 if _lib is None:
  _lib=C.CDLL(str(ROOT/'build/append/attention.so'));_lib.ll_error.restype=C.c_char_p
  for name in ['ll_launch','ll_append']:getattr(_lib,name).argtypes=[C.POINTER(P),C.POINTER(I),C.c_ulonglong]
 return _lib
class PagedDecodePlan:
 def __init__(self,q,k_cache,v_cache,block_table,lengths,new_k=None,new_v=None,workers=None,fused_finish=None):
  b,h,d=q.shape;physical,hk,page,kd=k_cache.shape;assert d==kd and page==16 and h%hk==0;g=h//hk;assert (d,g) in [(128,1),(128,4),(128,8),(256,4)]
  assert v_cache.shape==k_cache.shape and block_table.shape[0]==b and lengths.shape==(b,);npages=block_table.shape[1]
  # Length values and table bounds may change on-device; the caller guarantees
  # 1 <= length <= npages*16 and 0 <= block_table < physical_pages.
  tensors=[q,k_cache,v_cache,block_table,lengths]
  assert all(x.is_cuda and x.is_contiguous() and x.device==q.device for x in tensors)
  assert all(x.dtype==torch.float16 for x in tensors[:3]) and all(x.dtype==torch.int32 for x in tensors[3:])
  assert (new_k is None)==(new_v is None)
  if new_k is not None:
   assert new_k.shape==new_v.shape==(b,hk,d);assert all(x.is_cuda and x.is_contiguous() and x.device==q.device and x.dtype==torch.float16 for x in [new_k,new_v])
  if workers is None:
   candidates=[c for c in read(ROOT/'freeze/PROTOCOL.json')['cases'] if (c['B'],c['H'],c['HK'],c['D'],(c['L']+15)//16)==(b,h,hk,d,npages)]
   if not candidates:raise ValueError('Unmeasured shape: supply workers and fused_finish explicitly; no performance guarantee')
   selection=read(ROOT/'freeze/SELECTION.json')['cases'][candidates[0]['id']];fused_finish=selection['best_custom']=='FUSED';workers=selection['fused' if fused_finish else 'direct']
  assert workers in [1,4,8,16,32,64,128];fused_finish=bool(fused_finish)
  self.q=q;self.k=k_cache;self.v=v_cache;self.table=block_table;self.lengths=lengths;self.new_k=new_k;self.new_v=new_v;self.workers=workers;self.fused_finish=fused_finish
  self.counter=torch.zeros(b*hk*3,dtype=torch.int32,device=q.device);self.partial=torch.empty(b*hk*workers*g*(d+4),dtype=torch.float32,device=q.device);self.output=torch.empty_like(q)
  args=[q,k_cache,v_cache,block_table,lengths,None,self.counter,self.partial,self.output,None,new_k,new_v];self.yes=(P*12)(*[x.data_ptr() if x is not None else 0 for x in args]);args[10:]=[None,None];self.no=(P*12)(*[x.data_ptr() if x is not None else 0 for x in args]);self.cfg=(I*9)(d,g,b,hk,npages,workers,0,int(fused_finish),0);library()
 def launch(self,append='fused'):
  if append not in ['fused','separate','none']:raise ValueError('append must be fused, separate, or none')
  stream=torch.cuda.current_stream(self.q.device).cuda_stream;lib=library()
  def check(rc):
   if rc:raise RuntimeError(lib.ll_error().decode())
  if append!='none' and self.new_k is None:raise ValueError('Append inputs were not supplied')
  if append=='separate':check(lib.ll_append(self.yes,self.cfg,stream))
  check(lib.ll_launch(self.yes if append=='fused' else self.no,self.cfg,stream));return self.output
