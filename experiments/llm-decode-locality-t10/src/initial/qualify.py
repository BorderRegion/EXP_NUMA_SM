from runtime import *
import sys
out=Path(sys.argv[1]);rows=[];placements=[]
for D,G,L,B,HK in [(128,1,17,2,2),(128,4,63,2,2),(128,8,257,1,2),(256,4,33,1,2)]:
 c=dict(B=B,H=G*HK,HK=HK,D=D,L=L,lengths=[L-i*3 for i in range(B)])
 d=Data(c,970001+D+G,ring=2)
 for slot in range(2):
  for W in [1,4,16]:
   for fused in [0,1]:
    for mode in [0,1,2,3,4]:
     j=Job(d,slot,'CUSTOM',W,fused,mode);j.run(12);r=j.check();rows.append(dict(D=D,G=G,L=L,W=W,fused=fused,mode=mode,slot=slot,**r));j.close()
  for p in ['SDPA_IDEAL','SDPA_PAGED','BMM_IDEAL']:
   j=Job(d,slot,p);rows.append(dict(D=D,G=G,L=L,policy=p,slot=slot,**j.check()));j.close()
 for mode in [0,1,2,3,4]:
  j=Job(d,0,'CUSTOM',4,1,mode,trace=True);d.trace.zero_();torch.cuda.synchronize();j.run();a=d.trace.cpu().numpy().reshape(d.B*d.HK,d.NP,5);assert (a[:,:,4]==1).all();assert ((a[:,:,0]>=0)&(a[:,:,0]<56)).all();
  if mode:
   pref=(a[:,:,1]&1) if mode==1 else ((a[:,:,0]%10>=4)&(a[:,:,0]%10<=7)).astype(int)
   if mode==3:pref^=1
   assert np.array_equal(pref,a[:,:,2]);assert np.array_equal(a[:,:,3],np.array(d.labels['shuffle' if mode==4 else 'plain']))
  np.save(out/f'trace_D{D}_G{G}_L{L}_mode{mode}.npy',a);placements.append(dict(D=D,G=G,L=L,mode=mode,status='PASS',tasks=int(a.shape[0]*a.shape[1])));j.close()
 d.close();write(out/'numerical.json',rows);write(out/'placements.json',placements);print('QUALIFY',D,G,L,'PASS',flush=True)
write(out/'complete.json',dict(status='PASS',numerical=len(rows),traces=len(placements)));print('QUALIFICATION_PASS',len(rows),len(placements))
