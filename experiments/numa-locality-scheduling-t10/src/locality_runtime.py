from runtime import *
ext=C.CDLL(str(ROOT/'build/attention.so'));ext.ll_error.restype=C.c_char_p
for name in ['ll_launch','ll_append']:getattr(ext,name).argtypes=[C.POINTER(P),C.POINTER(I),C.c_ulonglong]
def echeck(x):
 if x:raise RuntimeError(ext.ll_error().decode())
class LocalData(Data):
 def __init__(self,c,seed,offset=0,ring=4):
  super().__init__(c,seed,offset,ring);assert self.D==128;t=time.perf_counter();n=self.k.numel()*2
  def replica(src):
   backing=torch.empty(n+262144//2+offset//2,device='cuda',dtype=torch.float16);self.alloc.append(backing);pad=((-backing.data_ptr())%262144+offset)//2
   dst=backing[pad:pad+n].view(-1,2,16,self.D);dst.copy_(src.view(-1,1,16,self.D).expand(-1,2,-1,-1));return dst
  start=torch.cuda.Event(enable_timing=True);end=torch.cuda.Event(enable_timing=True);start.record();self.rk=replica(self.k);self.rv=replica(self.v);end.record();end.synchronize()
  self.replica_gpu_ms=start.elapsed_time(end);self.replica_wall_ms=(time.perf_counter()-t)*1000
  assert ((self.rk.data_ptr()>>12)&0x33)==((self.rv.data_ptr()>>12)&0x33)
  self.meta.update(replica_k_va=self.rk.data_ptr(),replica_v_va=self.rv.data_ptr(),replica_bytes=n*2*2,replica_gpu_ms=self.replica_gpu_ms,replica_wall_ms=self.replica_wall_ms,replica_sha256=[tensor_sha(self.rk),tensor_sha(self.rv)])
  encoded=[]
  for b in range(self.B):
   order=np.argsort(np.array(self.meta['page_table'][b]))
   for hk in range(self.HK):encoded.append(np.concatenate(([0,0],order)))
  self.physical_list=torch.tensor(np.array(encoded),dtype=torch.int32,device='cuda')
  self.meta['physical_order']=[x[2:].tolist() for x in encoded]
  nk=[];nv=[]
  for b in range(self.B):
   pos=self.meta['lengths'][b]-1;page=self.meta['page_table'][b][pos//16]
   nk.append(self.k[page,:,pos%16,:]);nv.append(self.v[page,:,pos%16,:])
  self.nk=torch.stack(nk);self.nv=torch.stack(nv);torch.cuda.synchronize()

class LocalJob(Job):
 def __init__(self,d,slot,W,fused,mode,chunk=1,append=False,trace=False,legacy=False):
  self.legacy=legacy;self.append=append;self.extmode=mode
  k,v=(d.rk,d.rv) if 5<=mode<=9 else (d.k,d.v)
  ls=d.physical_list if mode==11 else d.lists['plain']
  args=[d.q[slot],k,v,d.table,d.length,ls,d.counter,d.partial,d.out,d.trace if trace else None,d.nk,d.nv]
  self.extargs=(P*12)(*[x.data_ptr() if x is not None else 0 for x in args]);self.extcfg=(I*10)(d.D,d.G,d.B,d.HK,d.NP,W,mode,fused,int(trace),chunk)
  super().__init__(d,slot,'LOCAL',W,fused,mode,trace)
 def op(self):
  stream=torch.cuda.current_stream().cuda_stream
  if self.append:echeck(ext.ll_append(self.extargs,self.extcfg,stream))
  if self.legacy:check(lib.ll_launch(self.extargs,self.extcfg,stream))
  else:echeck(ext.ll_launch(self.extargs,self.extcfg,stream))
  self.state['out']=self.d.out

def trace_check(d,config,path):
 j=LocalJob(d,0,**config,trace=True);d.trace.zero_();torch.cuda.synchronize();j.run();num=d.check(d.out,0)
 a=d.trace.cpu().numpy().reshape(d.B*d.HK,d.NP,5);assert (a[:,:,4]==1).all();assert ((a[:,:,0]>=0)&(a[:,:,0]<56)).all()
 mode=config['mode'];pref=((a[:,:,0]%10>=4)&(a[:,:,0]%10<=7)).astype(int)
 if mode in [1,5]:pref=a[:,:,1]&1
 if mode in [3,7]:pref^=1
 if mode==8:pref=((a[:,:,0]*17+13)^(a[:,:,0]>>2))&1
 if mode in range(1,10):assert np.array_equal(pref,a[:,:,2])
 if mode in [1,2,3]:assert np.array_equal(a[:,:,3],np.asarray(d.labels['plain']))
 if mode in [5,6,7,8]:assert np.array_equal(a[:,:,3],pref)
 assert not d.counter.count_nonzero().item();np.save(path,a);j.close()
 return dict(**num,tasks=int(a.shape[0]*a.shape[1]),actual_sms=len(np.unique(a[:,:,0])),preferred_fraction=float(np.mean(a[:,:,2]==a[:,:,3])) if mode in range(1,10) else None)
