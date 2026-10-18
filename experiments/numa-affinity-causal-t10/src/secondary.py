"""Exploratory complete-policy comparisons; never changes primary or selection."""
from common import *
from analyze import cells,key,summary
import collections,numpy as np
def run():
 rows=cells('confirm');selection=read(ROOT/'freeze/SELECTION.json')['choices'];groups=collections.defaultdict(list)
 for x in rows:groups[key(x)].append(x)
 out=[]
 for k,rr in groups.items():
  z=collections.defaultdict(dict)
  for x in rr:z[x['process'],x['block']][x['label']]=x
  for metric in ['gpu','host']:
   comparisons=[('POOLED','IDENTITY'),('POOLED','RANDOM_BEST'),('RANDOM_BEST','IDENTITY')]
   if rr[0]['V']==131072:comparisons += [('POOLED','BASE_IDENTITY'),('POOLED','BASE_MINIMAX'),('RANDOM_BEST','BASE_IDENTITY'),('RANDOM_BEST','BASE_MINIMAX')]
   for a,b in comparisons:
    actual=lambda n:selection[k]['policy'] if n=='RANDOM_BEST' else n
    byp=collections.defaultdict(list)
    for (proc,block),d in z.items():byp[proc].append(np.log(d[actual(a)][metric]/d[actual(b)][metric]))
    out.append(dict(**{f:rr[0][f] for f in ['V','variant','page','scope']},metric=metric,comparison=a+'/'+b,exploratory=True,**summary([np.mean(byp[p]) for p in sorted(byp)])))
 write(ROOT/'derived/SECONDARY.json',dict(analysis='Exploratory analysis specified during confirmation execution, before reading confirmation timing outcomes. Primary16comparisons unchanged. Random search gains are not address/topology attribution.',results=out));return out
if __name__=='__main__':run()
