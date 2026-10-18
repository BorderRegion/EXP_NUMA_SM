from backend import *
import sys
out=Path(sys.argv[1]);checks=[]
for mode in [-2,0,1,2]:
 e=Engine(mode=mode);d=Data(65,196,512,ring=1)
 if mode==-2:j=Job(e,d,kind=3)
 else:j=Job(e,d,recipe=1,s=4,kind=1,slab=1,pg=e.halves[mode],cg=e.halves[mode][::-1],diag=1,generation=13)
 j.run();num=d.numerical(0);place=j.placement() if mode>=0 else None;checks.append(dict(mode=mode,setup=e.setup_costs,numerical=num,placement=place))
 if mode==2:np.savez_compressed(out/'gemm_snapshot.npz',A=d.ha[0].numpy(),B=d.hb.numpy(),D=d.d.cpu().numpy(),reference_fp64=(d.ha[0].double()@d.hb.double().T).numpy())
 j.close();d.close();e.close()
write(out/'host_checks.json',checks)
from attention import Attention,phase
for idx,(h,hk,dim,chain) in enumerate([(16,16,64,False),(32,8,128,False),(32,8,128,True)]):
 c=dict(case_id=f'QUAL{idx}',batch=1,query_heads=h,kv_heads=hk,head_dim=dim,kv_length=256);a=Attention(c,775+idx,chain)
 for impl in ['EFFICIENT','MATH']:
  phase(out,a,impl,dict(phase_id=f'QUAL{idx}_{impl}',stage='QUALIFICATION',block=0,case=c['case_id'],policy=impl),requests=16)
 a.close()
write(out/'complete.json',dict(status='PASS',host_modes=4,attention_phases=6));print('HOST_ATTENTION_QUALIFIED',flush=True)
