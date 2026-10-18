from const_runtime import *
import sys
out=Path(sys.argv[1]);small='--small' in sys.argv;rows=[]
for V in ([32768] if small else [32768,65536,131072,262144]):
 d=ConstData(V,108900000+V,ring=1)
 for page in ([0] if small else [0,17,257]):
  for name in ['MINIMAX','IDENTITY','WORST','WRONG_ADDRESS','RND00','RND11','NATIVE']:
   for fresh in [False,True]:
    j=ConstJob(d,0,name,page,True,fresh);r=j.check()
    if name!='NATIVE':
     tr=d.trace.cpu().view(56,2).numpy();assert np.array_equal(np.sort(tr[:,0]),np.arange(56)) and np.array_equal(tr[:,0],tr[:,1]);r['roster_status']='PASS'
    rows.append(dict(V=V,page=page,policy=name,fresh=fresh,**r));write(out/'numerical.json',rows);j.close()
 d.close()
write(out/'complete.json',dict(status='PASS',checks=len(rows)));print('CONST_QUALIFY_PASS',len(rows))
