from dispatch import *
from backend import Engine,Data
from runtime import repeat
import sys,time
out=Path(sys.argv[1]);e=Engine();rows=[]
for m,n,k in [(1,1024,16384),(32,8192,4096),(48,2048,6144),(224,2560,10240),(17,320,1056)]:
 d=Data(m,n,k,s=2,seed=901,ring=2,workspace_words=required_workspace_words(m,n,k));js=[build_deployed(e,d,i) for i in range(2)]
 for slot,j in enumerate(js):
  repeat(j,5);r=d.numerical(slot);rows.append(dict(M=m,N=n,K=k,slot=slot,choice=choice(m,n,k),graph=j.dag,numerical=r));j.close()
 d.close()
e.close();write(out/'verification.json',rows);print('DEPLOYED_SHAPE_SELECTOR_PASS',len(rows))
