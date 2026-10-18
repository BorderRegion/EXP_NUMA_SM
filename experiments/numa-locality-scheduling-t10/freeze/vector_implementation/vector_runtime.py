from locality_runtime import *
libraries={}
for name,path in [('OLD','build/legacy/attention.so'),('OLD_APPEND','build/legacy/append.so'),('VECTOR','build/vector.so'),('VECTOR_APPEND','build/vector_append.so')]:
 z=C.CDLL(str(ROOT/path));z.ll_error.restype=C.c_char_p;z.ll_launch.argtypes=[C.POINTER(P),C.POINTER(I),C.c_ulonglong];libraries[name]=z
class VectorData(Data):
 def __init__(self,*args,**kwargs):
  super().__init__(*args,**kwargs);ks=[];vs=[]
  for b in range(self.B):
   pos=self.meta['lengths'][b]-1;p=self.meta['page_table'][b][pos//16];ks.append(self.k[p,:,pos%16,:]);vs.append(self.v[p,:,pos%16,:])
  self.nk=torch.stack(ks);self.nv=torch.stack(vs)
class VectorJob(Job):
 def __init__(self,d,slot,kind,W,fused,mode=0,append=False,trace=False):
  self.kind=kind;self.do_append=append;self.separate=kind=='PREVIOUS' and d.c.get('id')=='GQA8_LONG' and append
  k='OLD' if kind=='PREVIOUS' else kind;self.z=libraries[k+('_APPEND' if append and not self.separate else '')]
  args=[d.q[slot],d.k,d.v,d.table,d.length,d.lists['shuffle' if mode==4 else 'plain'],d.counter,d.partial,d.out,d.trace if trace else None,d.nk,d.nv]
  self.a=(P*12)(*[x.data_ptr() if x is not None else 0 for x in args]);self.c=(I*10)(d.D,d.G,d.B,d.HK,d.NP,W,mode,fused,int(trace),1)
  super().__init__(d,slot,'VECTOR_API',W,fused,mode,trace)
 def op(self):
  stream=torch.cuda.current_stream().cuda_stream
  if self.separate:echeck(ext.ll_append(self.a,self.c,stream))
  rc=self.z.ll_launch(self.a,self.c,stream)
  if rc:raise RuntimeError(self.z.ll_error().decode())
  self.state['out']=self.d.out
def configs(c):
 s=read(ROOT/'freeze/LEGACY_SELECTION.json')['cases'][c['id']];f=int(s['best_custom']=='FUSED');w=s['fused' if f else 'direct']
 cfg={kind+'_'+name:dict(kind=kind,W=w,fused=f,mode=mode) for kind in ['OLD','VECTOR'] for name,mode in [('DIRECT',0),('BLIND',1),('MATCH',2),('INVERT',3),('SHUFFLE',4)]}
 cfg['PREVIOUS']=dict(kind='PREVIOUS',W=w,fused=f,mode=0);return cfg
