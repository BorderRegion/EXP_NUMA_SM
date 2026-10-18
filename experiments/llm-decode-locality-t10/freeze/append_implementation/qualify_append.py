from runtime import *
from kernel_api import PagedDecodePlan
import sys
out=Path(sys.argv[1]);rows=[]
for D,G in [(128,1),(128,4),(128,8),(256,4)]:
 d=Data(dict(B=2,H=G*2,HK=2,D=D,L=79,lengths=[79,58]),887000+D+G,ring=2);gen=torch.Generator(device='cpu').manual_seed(88+D)
 nk=(torch.rand((2,2,D),generator=gen)*2-1).half().cuda();nv=(torch.rand((2,2,D),generator=gen)*2-1).half().cuda()
 for W in [1,16,128]:
  for finish in [False,True]:
   for mode in ['separate','fused']:
    plan=PagedDecodePlan(d.q[0],d.k,d.v,d.table,d.length,nk,nv,W,finish)
    for lengths in [[1,7],[17,31],[79,58]]:
     expected_k=d.k.clone();expected_v=d.v.clone();d.length.copy_(torch.tensor(lengths,device='cuda',dtype=torch.int32))
     for b,pos in enumerate(lengths):
      page=int(d.table[b,(pos-1)//16]);expected_k[page,:,(pos-1)%16]=nk[b];expected_v[page,:,(pos-1)%16]=nv[b]
     for _ in range(5):plan.launch(mode)
     torch.cuda.synchronize();assert torch.equal(d.k,expected_k) and torch.equal(d.v,expected_v);assert not plan.counter.count_nonzero().item();d.ideal_k,d.ideal_v=d.gather();d.mask=(torch.arange(d.capacity,device='cuda')[None,:]<d.length[:,None]).view(d.B,1,1,d.capacity);d.refs={};d.fp64={}
     rows.append(dict(D=D,G=G,W=W,finish=finish,mode=mode,lengths=lengths,cache_exact='PASS',**d.check(plan.output,0)))
    del plan
 d.close();write(out/'numerical.json',rows)
print('APPEND_QUALIFICATION_PASS',len(rows));write(out/'complete.json',dict(status='PASS',checks=len(rows)))
