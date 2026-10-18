from backend import *
import sys
out=Path(sys.argv[1]);e=Engine();d=Data(17,132,512,ring=1)
for mode in ['random','zero','cancellation','tiny']:
 if mode=='zero':d.ha[0].zero_();d.hb.zero_()
 elif mode=='cancellation':
  d.ha[0].fill_(1);d.hb[:,::2]=1;d.hb[:,1::2]=-1
 elif mode=='tiny':d.ha[0].fill_(2**-12);d.hb.fill_(2**-12)
 d.a[0].copy_(d.ha[0]);d.b.copy_(d.hb);d.refs={};d.fp64_refs={};torch.cuda.synchronize()
 for slab in [0,1]:
  j=Job(e,d,recipe=1,s=4,kind=1,slab=slab,pg=e.halves[0],cg=e.halves[0][::-1],diag=1,generation=11,stages=1,scratch=int(mode=='random'))
  place=j.placement();num=d.numerical(0);append(out/'correctness.jsonl',dict(mode=mode,slab=slab,numerical=num,placement=place));j.close()
d.close();e.close();write(out/'result.json',dict(status='PASS',checks=8));print('EDGE_PASS',flush=True)
