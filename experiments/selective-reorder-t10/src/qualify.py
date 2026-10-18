from backend import *
import sys
out=Path(sys.argv[1]);small=len(sys.argv)>2
records=[]
e=Engine();assert e.state()==dict(enumerated_2sm_resources=0,green_contexts=0,math_module_loaded=0,diag_module_loaded=0,blas_loaded=0)
d=Data(17,196,512,ring=1);j=Job(e,d,kind=3,s=1);j.run();num=d.numerical(0);state=e.state();assert state['enumerated_2sm_resources']==0 and state['green_contexts']==0 and state['diag_module_loaded']==0 and state['math_module_loaded']==0 and d.w is None and d.trace is None
check(lib.sr_run_async(j.ptr));check(lib.sr_wait(e.ptr));d.numerical(0)
append(out/'qualifications.jsonl',dict(test='NATIVE_LIB_DIRECT_AND_ASYNC',state=state,numerical=num,dag=j.dag,workspace_bytes=0,diag_buffer_bytes=0));j.close();d.close();e.close()
e=Engine(mode=-1,diagnostic=True)
for m,n,k in ([(17,196,512)] if small else [(1,132,256),(17,196,512),(65,260,768)]):
 c=dict(M=m,N=n,K=k);d=Data(m,n,k,s=4,ring=1,workspace_words=workspace(c,3,4,True),diagnostic=True)
 for recipe in ([3] if small else [0,2,3]):
  for s in ([2] if small else [2,4]):
   for alpha,beta in ([(1,0)] if small else [(1,0),(.75,.25)]):
    d.c.fill_(.125);torch.cuda.synchronize();native=Job(e,d,recipe=recipe,s=s,kind=0,alpha=alpha,beta=beta);native.run();num=d.numerical(0,alpha,beta);bits=d.d.cpu().view(torch.int32).clone();native.close()
    for part in range(3):
     for pi in range(2):
      pg=e.halves[part];cg=pg[::-1] if pi else pg;j=Job(e,d,recipe=recipe,s=s,kind=1,slab=1,pg=pg,cg=cg,alpha=alpha,beta=beta);j.run();num=d.numerical(0,alpha,beta);assert torch.equal(bits,d.d.cpu().view(torch.int32));append(out/'qualifications.jsonl',dict(test='PRODUCTION_RAW_BITS',shape=[m,n,k],recipe=recipe,S=s,part=part,pi=pi,numerical=num,raw_bit_equal=True,dag=j.dag));j.close()
   j=Job(e,d,recipe=recipe,s=s,kind=1,slab=1,pg=e.halves[1],cg=e.halves[1][::-1],diag=1,generation=19);p=j.placement();append(out/'placement.jsonl',p);j.close()
  j=Job(e,d,recipe=recipe,s=1,kind=4);j.run();append(out/'qualifications.jsonl',dict(test='SINGLE',recipe=recipe,numerical=d.numerical(0)));j.close()
 d.close()
write(out/'roster.json',dict(groups=e.membership,quad=e.quad,halves=e.halves,resources=e.state()));e.close();write(out/'complete.json',dict(status='PASS'))
