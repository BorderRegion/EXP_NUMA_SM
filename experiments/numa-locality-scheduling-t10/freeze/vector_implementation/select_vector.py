from common import *
from select_config import load
import numpy as np
def compute():
 result={}
 for c in read(ROOT/'freeze/PROTOCOL.json')['cases']:
  result[c['id']]={}
  for mode in ['attention','append']:
   scores={n:[] for n in ['VECTOR_DIRECT','VECTOR_BLIND']};old={n:[] for n in ['OLD_DIRECT','OLD_BLIND','PREVIOUS']}
   for p in range(2):
    for offset in [0,65536]:
     _,g=load(RUN/f'vector_dev_{p}'/c['id']/f'offset_{offset}'/mode/'requests.csv.gz')
     for b in range(8):
      for name,store in [*[(n,scores) for n in scores],*[(n,old) for n in old]]:store[name].append(np.log(g[b,name]['gpu_us']/g[b,'PREVIOUS']['gpu_us']))
   scores={k:float(np.mean(v)) for k,v in scores.items()};old={k:float(np.mean(v)) for k,v in old.items()}
   result[c['id']][mode]=dict(candidate=min(scores,key=lambda k:(scores[k],k)),strong_old=min(old,key=lambda k:(old[k],k)),candidate_scores=scores,old_scores=old)
 return dict(cases=result)
if __name__=='__main__':x=compute();x['frozen_utc']=utc();write(ROOT/'freeze/VECTOR_SELECTION.json',x);print(x)
