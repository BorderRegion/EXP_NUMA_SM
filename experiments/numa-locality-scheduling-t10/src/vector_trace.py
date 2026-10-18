from vector_runtime import *
import sys
out=Path(sys.argv[1]);rows=[]
for ci,c in enumerate(read(ROOT/'freeze/PROTOCOL.json')['cases']):
 for off in [0,65536]:
  d=VectorData(c,98000000+ci*101,off,ring=1);base=configs(c)['VECTOR_DIRECT']
  for append in [False,True]:
   for mode in [0,1,2,3,4]:
    cfg=dict(base,mode=mode);j=VectorJob(d,0,**cfg,append=append,trace=True);d.trace.zero_();torch.cuda.synchronize();j.run();num=d.check(d.out,0);assert not d.counter.count_nonzero().item();a=d.trace.cpu().numpy().reshape(d.B*d.HK,d.NP,5);assert (a[:,:,4]==1).all();assert ((a[:,:,0]>=0)&(a[:,:,0]<56)).all()
    if mode:
     pref=(a[:,:,1]&1) if mode==1 else ((a[:,:,0]%10>=4)&(a[:,:,0]%10<=7)).astype(int)
     if mode==3:pref^=1
     assert np.array_equal(pref,a[:,:,2]);assert np.array_equal(a[:,:,3],np.asarray(d.labels['shuffle' if mode==4 else 'plain']))
    path=f'{c["id"]}_{off}_{int(append)}_{mode}.npy';np.save(out/path,a);rows.append(dict(case=c['id'],offset=off,append=append,mode=mode,path=path,tasks=d.B*d.HK*d.NP,actual_sms=len(np.unique(a[:,:,0])),preferred_fraction=float(np.mean(a[:,:,2]==a[:,:,3])) if mode else None,**num));j.close()
  d.close();write(out/'verification.json',rows)
write(out/'complete.json',dict(status='PASS',checks=len(rows)));print('VECTOR_TRACE_PASS',len(rows))
