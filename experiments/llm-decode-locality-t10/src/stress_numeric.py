from runtime import *
from kernel_api import PagedDecodePlan
import sys
out=Path(sys.argv[1]);rows=[]
for D,G in [(128,4),(128,8),(256,4)]:
 d=Data(dict(B=2,H=G*2,HK=2,D=D,L=79,lengths=[79,35]),996101+D+G,ring=1);q0=d.q[0].clone();k0=d.k.clone()
 for kind,qs,ks in [('zero_logits',0,1),('peaked_logits',16,8)]:
  d.q[0].copy_(q0*qs);d.k.copy_(k0*ks);d.ideal_k,d.ideal_v=d.gather();d.refs={};d.fp64={}
  for f in [0,1]:
   j=Job(d,0,'CUSTOM',16,f,0);rows.append(dict(D=D,G=G,kind=kind,finish=f,scope='CORE',**j.check()));j.close()
  nk=torch.full((2,2,D),.75*ks,dtype=torch.float16,device='cuda');nv=torch.full_like(nk,-.25)
  for finish in [False,True]:
   p=PagedDecodePlan(d.q[0],d.k,d.v,d.table,d.length,nk,nv,16,finish);p.launch('fused');torch.cuda.synchronize();d.ideal_k,d.ideal_v=d.gather();d.refs={};d.fp64={};rows.append(dict(D=D,G=G,kind=kind,finish=finish,scope='FUSED_APPEND',**d.check(p.output,0)));del p
 d.close()
write(out/'numerical.json',rows);write(out/'complete.json',dict(status='PASS',checks=len(rows)));print('NUMERIC_STRESS_PASS',len(rows))
