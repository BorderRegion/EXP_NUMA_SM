from runtime import *
from optimized_decode import OptimizedPagedDecode
import sys
out=Path(sys.argv[1]);checks=[];cases=read(ROOT/'freeze/PROTOCOL.json')['cases']+[dict(id='UNKNOWN',B=2,H=8,HK=2,D=128,L=79,lengths=[79,53])]
for c in cases:
 d=Data(c,9900001+len(checks),ring=2);nk=torch.full((d.B,d.HK,d.D),.2,dtype=torch.float16,device='cuda');nv=torch.full_like(nk,-.7)
 for slot in range(2):
  kw=dict(workers=16,fused_finish=False) if c['id']=='UNKNOWN' else {};p=OptimizedPagedDecode(d.q[slot],d.k,d.v,d.table,d.length,nk,nv,**kw)
  for mode in ['auto','none']:
   for _ in range(2):p.launch(mode)
   torch.cuda.synchronize();g=torch.cuda.CUDAGraph(keep_graph=True)
   with torch.cuda.graph(g):y=p.launch(mode)
   g.instantiate();g.replay();torch.cuda.synchronize();d.ideal_k,d.ideal_v=d.gather();d.refs={};d.fp64={};r=d.check(y,slot);assert not p.counter.count_nonzero().item();dag=json.loads(lib.ll_dag(g.raw_cuda_graph()));n=sum(x['type']==0 for x in dag['nodes']);expected=(1 if p.fused_finish else 2)+(mode=='auto' and p.recommended=='legacy_separate');assert n==expected
   checks.append(dict(case=c['id'],slot=slot,mode=mode,recommended=p.recommended,kernels=n,graph=dag,**r));del g
  del p
 d.close()
write(out/'verification.json',checks);write(out/'complete.json',dict(status='PASS',checks=len(checks)));print('PUBLIC_API_PASS',len(checks))
