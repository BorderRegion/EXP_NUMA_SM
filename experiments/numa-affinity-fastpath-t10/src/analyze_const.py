from analyze import logs,summary
from common import *
import numpy as np,csv,gzip,collections
def get_cells():
 rows=[]
 for worker in sorted(RUN.glob('const_confirm_*')):
  process=int(worker.name.rsplit('_',1)[1])
  for path in sorted(worker.glob('*/*/offset_*/requests.csv.gz')):
   z=collections.defaultdict(list)
   with gzip.open(path,'rt') as f:
    for x in csv.DictReader(f):
     if x['phase']=='test':z[int(x['block']),x['label']].append([float(x['gpu_us']),float(x['host_us'])])
   for (block,label),vv in z.items():
    v=np.array(vv);rows.append(dict(scope=path.parent.parent.parent.name,case=path.parent.parent.name,offset=int(path.parent.name.split('_')[1]),process=process,block=block,label=label,gpu=float(np.median(v[:,0])),host=float(np.median(v[:,1])),requests=len(v)))
 return rows
def run():
 rows=get_cells();z=collections.defaultdict(list)
 for x in rows:
  if x['label'].startswith('RND'):z[x['scope'],x['case'],x['offset'],x['process'],x['block']].append(x)
 for key,a in z.items():
  assert len(a)==12;rows.append(dict(scope=key[0],case=key[1],offset=key[2],process=key[3],block=key[4],label='RANDOM_POOL',gpu=float(np.exp(np.mean(np.log([v['gpu'] for v in a])))),host=float(np.exp(np.mean(np.log([v['host'] for v in a])))),requests=sum(v['requests'] for v in a)))
 results=[];cases=sorted({x['case'] for x in rows})
 for scope in ['ready','fresh']:
  for page in ['ALL',0,17,257]:
   sub=[x for x in rows if x['scope']==scope and (page=='ALL' or x['offset']==page)]
   for metric in ['gpu','host']:
    for a,b in [('MINIMAX',c) for c in ['NATIVE','IDENTITY','RANDOM_POOL','WORST','WRONG_ADDRESS','OLD_IDENTITY','OLD_MINIMAX']]+[('IDENTITY','NATIVE'),('OLD_MINIMAX','OLD_IDENTITY')]:
     v=logs(sub,a,b,metric)
     for case in ['ALL']+cases:
      vv=v if case=='ALL' else [x for x in v if x['case']==case];s=summary(vv);p=np.log1p(-np.array(s['process_gain_pct'])/100);rng=np.random.default_rng(20261018);bs=p[rng.integers(0,len(p),(30000,len(p)))].mean(axis=1);s['ci99375_pct']=np.sort(-100*np.expm1(np.quantile(bs,[.003125,.996875]))).tolist()
      results.append(dict(scope=scope,address=page,case=case,metric=metric,comparison=a+'/'+b,**s))
 write(ROOT/'derived/const_confirm.json',dict(results=results,cells=rows))
 for x in results:
  if x['address']=='ALL' and x['metric']=='gpu' and x['comparison'] in ['MINIMAX/IDENTITY','MINIMAX/RANDOM_POOL','MINIMAX/WRONG_ADDRESS','MINIMAX/NATIVE']:print(x['scope'],x['case'],x['comparison'],round(x['gain_pct'],4),x['ci95_pct'])
if __name__=='__main__':run()
