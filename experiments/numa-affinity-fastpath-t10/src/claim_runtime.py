from runtime import *
libs={}
for name,path in [('FAST','build/baseline/vector_append.so'),('CA','build/claim_ca.so'),('CG','build/claim_cg.so')]:
 z=C.CDLL(str(ROOT/path));z.ll_error.restype=C.c_char_p;z.ll_launch.argtypes=[C.POINTER(P),C.POINTER(I),C.c_ulonglong];libs[name]=z

class ClaimData(Data):
 def __init__(self,*args,**kw):
  super().__init__(*args,**kw);ks=[];vs=[]
  for b in range(self.B):
   pos=self.meta['lengths'][b]-1;p=self.meta['page_table'][b][pos//16];ks.append(self.k[p,:,pos%16,:]);vs.append(self.v[p,:,pos%16,:])
  self.nk=torch.stack(ks);self.nv=torch.stack(vs);self.joblists={};self.plan_metadata={}
 def plan(self,W,shuffle):
  key=(W,shuffle)
  if key not in self.joblists:
   t=time.perf_counter();stride=(self.NP+W//2-1)//(W//2);encoded=[];stats=[]
   for head in range(self.B*self.HK):
    labels=np.array(self.labels['shuffle' if shuffle else 'plain'][head]);rows=np.full((W,stride),-1,np.int32)
    for cl in [0,1]:
     pages=np.flatnonzero(labels==cl)
     # Balanced interleaving of each color. Each valid page occurs exactly once.
     for j in range(W//2):
      subset=pages[j::W//2];rows[cl*(W//2)+j,:len(subset)]=subset
    actual=rows[rows>=0];assert sorted(actual.tolist())==list(range(self.NP))
    encoded.append(np.concatenate(([W//2,W//2,stride],rows.ravel())))
    stats.append(dict(head=head,page_counts=(rows>=0).sum(axis=1).tolist(),jobs=rows.tolist()))
   self.joblists[key]=torch.tensor(np.array(encoded),dtype=torch.int32,device='cuda');torch.cuda.synchronize()
   self.plan_metadata[str(key)]=dict(build_ms=(time.perf_counter()-t)*1000,bytes=self.joblists[key].numel()*4,heads=stats,sha256=tensor_sha(self.joblists[key]))
  return self.joblists[key]

class ClaimJob(Job):
 def __init__(self,d,slot,kind,W,fused,mode=0,trace=False):
  self.z=libs[kind];self.kind=kind
  ls=d.lists['shuffle' if mode==4 else 'plain'] if kind=='FAST' else d.plan(W,mode==4)
  args=[d.q[slot],d.k,d.v,d.table,d.length,ls,d.counter,d.partial,d.out,d.trace if trace else None,d.nk,d.nv]
  self.a=(P*12)(*[x.data_ptr() if x is not None else 0 for x in args]);self.c=(I*9)(d.D,d.G,d.B,d.HK,d.NP,W,mode,fused,int(trace))
  super().__init__(d,slot,'CLAIM',W,fused,mode,trace)
 def op(self):
  rc=self.z.ll_launch(self.a,self.c,torch.cuda.current_stream().cuda_stream)
  if rc:raise RuntimeError(self.z.ll_error().decode())
  self.state['out']=self.d.out

def configs(c,phase):
 W=16 if c['id']=='BATCH4_RAGGED' else 32;fused=int(c['id']=='GQA4_SHORT');blind=int(c['id'] in ['GQA4_LONG','GQA8_LONG'])
 cfg={'FAST':dict(kind='FAST',W=W,fused=fused,mode=blind)}
 if phase=='dev':
  for k in ['CA','CG']:
   for name,mode in [('BLIND',1),('MATCH',2),('INVERT',3),('SHUFFLE',4),('STATIC',5)]:cfg[k+'_'+name]=dict(kind=k,W=W,fused=fused,mode=mode)
 else:
  k=read(ROOT/'freeze/CLAIM_SELECTION.json')['cases'][c['id']]['kind']
  for name,mode in [('BLIND',1),('MATCH',2),('INVERT',3),('SHUFFLE',4),('STATIC',5)]:cfg[name]=dict(kind=k,W=W,fused=fused,mode=mode)
 return cfg
