from soft_runtime import *
import sys
out=Path(sys.argv[1]);small='--small' in sys.argv;rows=[]
for V in ([32768] if small else [32768,65536,131072,262144]):
 d=SoftData(V,103900000+V,ring=1)
 for page in ([0] if small else [0,17,257]):
  for name in ['TORCH','NATIVE']+[k[1] for k in d.maps if k[0]==page]:
   j=SoftJob(d,0,name,page,True);r=j.check()
   if name not in ['TORCH','NATIVE']:
    tr=d.trace.cpu().view(56,2).numpy();np.save(out/f'roster_{V}_{page}_{name}.npy',tr);assert np.array_equal(np.sort(tr[:,0]),np.arange(56)) and np.array_equal(tr[:,0],tr[:,1]);r['roster_status']='PASS'
   rows.append(dict(V=V,page=page,policy=name,**r));write(out/'numerical.json',rows);j.close()
 d.close()
write(out/'complete.json',dict(status='PASS',checks=len(rows)));print('SOFTMAX_QUALIFY_PASS',len(rows))
