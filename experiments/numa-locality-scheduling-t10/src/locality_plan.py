"""Single-copy paged decode plan; setup is separate and measured.

The original paged KV layout and cache remain authoritative. Page table entries
must remain fixed while a plan is used; changing allocation requires rebuilding
the lists. Valid lengths may change on-device within the fixed capacity. One
private plan/workspace per concurrent stream, private/COW terminal write pages.
Explicit policies are experimental; DEPLOY reads post-confirmation decisions.
The replica experiment is not exposed as a drop-in mutable-cache interface.
"""
from common import *
import ctypes as C, time
import numpy as np, torch
P=C.c_void_p;I=C.c_int
_libs={}
def library(name):
 if name not in _libs:
  p={'new':'attention.so','legacy':'legacy/attention.so','previous_append':'legacy/append.so','vector':'vector.so','vector_append':'vector_append.so'}[name]
  z=C.CDLL(str(ROOT/'build'/p));z.ll_error.restype=C.c_char_p;z.ll_launch.argtypes=[C.POINTER(P),C.POINTER(I),C.c_ulonglong]
  if name=='new':z.ll_append.argtypes=[C.POINTER(P),C.POINTER(I),C.c_ulonglong]
  _libs[name]=z
 return _libs[name]
def checked(z,code):
 if code:raise RuntimeError(z.ll_error().decode())
class LocalityPlan:
 def __init__(self,q,k,v,table,lengths,new_k=None,new_v=None,policy='DEPLOY'):
  t=time.perf_counter();b,h,d=q.shape;physical,hk,page,kd=k.shape
  assert d==kd==128 and page==16 and h%hk==0 and h//hk in [1,4,8]
  assert k.shape==v.shape and table.ndim==2 and table.shape[0]==b and lengths.shape==(b,)
  assert all(x.is_cuda and x.is_contiguous() and x.device==q.device for x in [q,k,v,table,lengths])
  assert all(x.dtype==torch.float16 for x in [q,k,v]) and all(x.dtype==torch.int32 for x in [table,lengths])
  assert (new_k is None)==(new_v is None)
  if new_k is not None:assert new_k.shape==new_v.shape==(b,hk,d) and all(x.is_cuda and x.is_contiguous() and x.device==q.device and x.dtype==torch.float16 for x in [new_k,new_v])
  npages=table.shape[1];cases=read(ROOT/'freeze/PROTOCOL.json')['cases'];cid=next((c['id'] for c in cases if [c['B'],c['H'],c['HK'],c['D'],(c['L']+15)//16]==[b,h,hk,d,npages]),None)
  if cid is None:raise ValueError('Unmeasured shape: no automatic performance dispatch')
  requested=policy
  if policy=='DEPLOY':policy=read(ROOT/'freeze/DEPLOYMENT_POLICY.json')['cases'][cid]['append' if new_k is not None else 'attention']
  old=read(ROOT/'freeze/LEGACY_SELECTION.json')['cases'][cid];f=int(old['best_custom']=='FUSED');w=old['fused' if f else 'direct'];mode=0;chunk=1
  self.backend='legacy';self.previous_fused=policy=='PREVIOUS_DEPLOYED' and new_k is not None and cid!='GQA8_LONG';self.fused_append_backend='previous_append'
  if policy not in ['LEGACY','PREVIOUS_DEPLOYED']:
   sel=read(ROOT/'freeze/SELECTION.json')['cases'][cid]
   if policy in ['VECTOR_DIRECT','VECTOR_BLIND','VECTOR_MATCH','VECTOR_INVERT']:
    if k.data_ptr()%16 or v.data_ptr()%16:raise ValueError('Vector KV loads require 16-byte aligned contiguous cache tensors')
    cfg=dict(W=w,fused=f,mode={'VECTOR_DIRECT':0,'VECTOR_BLIND':1,'VECTOR_MATCH':2,'VECTOR_INVERT':3}[policy]);self.backend='vector';self.previous_fused=new_k is not None;self.fused_append_backend='vector_append'
   elif policy=='STATIC':cfg=sel['static']
   elif policy in ['COARSE_BLIND','COARSE_MATCH','COARSE_INVERT']:cfg=dict(sel['coarse'],mode={'COARSE_BLIND':1,'COARSE_MATCH':2,'COARSE_INVERT':3}[policy])
   else:raise ValueError('Supported: DEPLOY, LEGACY, PREVIOUS_DEPLOYED, STATIC, COARSE_BLIND/MATCH/INVERT, VECTOR_DIRECT/BLIND/MATCH/INVERT')
   w,f,mode,chunk=cfg['W'],cfg['fused'],cfg['mode'],cfg.get('chunk',1)
   if self.backend!='vector':self.backend='new'
  self.refs=[q,k,v,table,lengths,new_k,new_v];self.counter=torch.zeros(b*hk*3,dtype=torch.int32,device=q.device)
  self.partial=torch.empty(b*hk*w*(h//hk)*(d+4),dtype=torch.float32,device=q.device);self.output=torch.empty_like(q);self.lists=None
  if mode in [1,2,3,11]:
   pages=table.cpu().numpy();assert ((pages>=0)&(pages<physical)).all();encoded=[]
   for batch in range(b):
    for head in range(hk):
     if mode==11:row=np.concatenate(([0,0],np.argsort(pages[batch])))
     else:
      cls=np.array([(((k.data_ptr()+(int(p)*hk+head)*4096)>>12)&0x33).bit_count()%2 for p in pages[batch]])
      a=np.flatnonzero(cls==0);o=np.flatnonzero(cls==1);row=np.concatenate(([len(a),len(o)],a,o))
     encoded.append(row)
   self.lists=torch.tensor(np.array(encoded),dtype=torch.int32,device=q.device)
  args=[q,k,v,table,lengths,self.lists,self.counter,self.partial,self.output,None,new_k,new_v]
  self.args=(P*12)(*[x.data_ptr() if x is not None else 0 for x in args]);self.cfg=(I*10)(d,h//hk,b,hk,npages,w,mode,f,0,chunk)
  self.case=cid;self.policy=policy;self.requested=requested
  for name in ['new','legacy','previous_append','vector','vector_append']:library(name)
  torch.cuda.current_stream(q.device).synchronize();self.setup_ms=(time.perf_counter()-t)*1000
 def launch(self):
  stream=torch.cuda.current_stream(self.refs[0].device).cuda_stream
  if self.previous_fused:
   z=library(self.fused_append_backend);checked(z,z.ll_launch(self.args,self.cfg,stream))
  else:
   if self.refs[5] is not None:
    z=library('new');checked(z,z.ll_append(self.args,self.cfg,stream))
   z=library(self.backend);checked(z,z.ll_launch(self.args,self.cfg,stream))
  return self.output
