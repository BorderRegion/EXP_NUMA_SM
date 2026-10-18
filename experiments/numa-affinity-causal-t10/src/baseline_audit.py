"""Post-run diagnostic of instruction-identical OLD vs exact prior binary."""
from common import *
from analyze import cells,summary
import collections,numpy as np
def run():
 rows=[x for x in cells('confirm') if x['V']==131072 and x['variant']=='OLD' and x['page']==17];out=[]
 for scope in ['ready','fresh','batch','freshbatch']:
  z=collections.defaultdict(dict)
  for x in rows:
   if x['scope']==scope:z[x['process'],x['block']][x['label']]=x
  for metric in ['gpu','host']:
   for policy in ['IDENTITY','MINIMAX']:
    v=collections.defaultdict(list)
    for (p,b),a in z.items():v[p].append(np.log(a[policy][metric]/a['BASE_'+policy][metric]))
    out.append(dict(scope=scope,metric=metric,comparison='OLD_'+policy+'/BASE_'+policy,**summary([np.mean(v[p]) for p in sorted(v)])))
 write(ROOT/'derived/BASELINE_AA.json',dict(note='Post-run performance consistency diagnostic; same instructions and schedule, separately compiled entry/function address and graph. No selection/exclusions.',results=out));return out
if __name__=='__main__':run()
