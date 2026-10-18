from runtime import *
import sys
out=Path(sys.argv[1]);e=Engine();records=[]
for recipe,bm,bn in [(0,32,64),(2,64,128)]:
 for s in [2,16]:
  d=Data(17,320,1056,s=s,seed=91,ring=2,workspace_words=17*320*s);counter=torch.zeros(((17+bm-1)//bm)*((320+bn-1)//bn),dtype=torch.int32,device='cuda')
  for kind in [0,12]:
   js=[Job(e,d,recipe=recipe,s=s,kind=kind,slab=1024,counters=counter,slot=slot) for slot in range(2)]
   for t in range(40):
    j=js[t%2];j.run()
    if t in [0,1,38,39]:records.append(dict(recipe=recipe,s=s,kind=kind,slot=t%2,**d.numerical(t%2)))
   assert not counter.count_nonzero().item()
   for j in js:j.close()
  d.close()
e.close();write(out/'qualification.json',records);print('ADDITIONAL_SPLITS_PASS',len(records))
