from backend import *
import sys
out=Path(sys.argv[1]);e=Engine();write(out/'environment.json',dict(engine_ms=e.init_ms,roster_ms=e.roster_ms,membership=e.membership,quad=e.quad,halves=e.halves,torch=torch.__version__,device=torch.cuda.get_device_name()))
checks=0
for idx,(m,n,k) in enumerate([(3,68,256),(65,196,288),(128,512,1024),(1,1024,4096)]):
 d=Data(m,n,k,seed=101+idx,ring=2)
 for recipe in range(4):
  for s in [1,2,4]:
   if k//s<32:continue
   j=Job(e,d,recipe,s,kind=0,stages=1);times=j.run();num=d.numerical(0);baseline=d.d.cpu().contiguous().numpy().view('uint32').copy();j.close();append(out/'correctness.jsonl',dict(shape=[m,n,k],recipe=recipe,S=s,kind='CORE',numerical=num,times_us=times));checks+=1
   for kind,slab,rev in [(5,0,0),(5,1,0),(1,0,0),(1,1,0),(1,1,1),(2,0,0),(2,1,1)]:
    pg=e.halves[0] if kind==1 else [e.quad[0],e.quad[0]];cg=pg[::-1] if rev else pg
    for diag in [0,1] if kind in [1,2] else [0]:
     j=Job(e,d,recipe,s,kind=kind,slab=slab,pg=pg,cg=cg,diag=diag,generation=7,task_reverse=rev,submit_reverse=rev,stages=1)
     times=j.run();num=d.numerical(0);bitwise=np.array_equal(baseline,d.d.cpu().contiguous().numpy().view('uint32'))
     if not bitwise:raise RuntimeError(f'BITWISE_MISMATCH {idx} {recipe} {s} {kind} {slab} {diag}')
     placement=j.placement() if diag else None
     append(out/'correctness.jsonl',dict(shape=[m,n,k],recipe=recipe,S=s,kind=kind,layout=slab,reverse=rev,diagnostic=diag,bitwise=bitwise,numerical=num,placement=placement,times_us=times));checks+=1;j.close()
  for kind in [3,4]:
   j=Job(e,d,recipe,1,kind=kind);times=j.run();num=d.numerical(0);append(out/'correctness.jsonl',dict(shape=[m,n,k],recipe=recipe,S=1,kind=kind,numerical=num,times_us=times));j.close();checks+=1
 d.close();print('QUALIFIED',idx,m,n,k,checks,flush=True)
# beta and alpha are applied once after all partial sums.
d=Data(17,132,512,seed=83,ring=1);d.c.fill_(.3)
for slab in [0,1]:
 j=Job(e,d,1,4,kind=1,slab=slab,pg=e.halves[0],cg=e.halves[0][::-1],alpha=.75,beta=.25);j.run();num=d.numerical(0,.75,.25);append(out/'correctness.jsonl',dict(kind='alpha_beta',slab=slab,numerical=num));j.close();checks+=1
d.close();e.close();write(out/'result.json',dict(status='PASS',checks=checks));print('ALL_PASS',checks,flush=True)
