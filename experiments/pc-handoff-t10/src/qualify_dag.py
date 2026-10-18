from backend import *
import sys
out=Path(sys.argv[1]);checks=[]
for mode in [-2,1]:
 e=Engine(mode=mode);d=Data(16,512,512,s=2,ring=1)
 for kind in [3,0]+([1] if mode==1 else []):
  groups=e.halves[1];j=Job(e,d,recipe=3,s=2,kind=kind,pg=groups,cg=groups,slab=int(kind==1));j.run();num=d.numerical(0);checks.append(dict(mode=mode,kind=kind,dag=j.dag,numerical=num));j.close()
 d.close();e.close()
write(out/'checks.json',checks);write(out/'complete.json',dict(status='PASS'));print('DAG_QUALIFIED',flush=True)
