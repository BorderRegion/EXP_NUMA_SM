from analyze import logs,summary
from common import *
import numpy as np,csv,gzip,collections,sys
def cells(phase):
 rows=[]
 for worker in sorted(RUN.glob('soft_'+phase+'_*')):
  process=int(worker.name.rsplit('_',1)[1])
  for path in sorted(worker.glob('*/offset_*/requests.csv.gz')):
   z=collections.defaultdict(list)
   with gzip.open(path,'rt') as f:
    for x in csv.DictReader(f):
     if x['phase']=='test':z[int(x['block']),x['label']].append([float(x['gpu_us']),float(x['host_us'])])
   for (block,label),vv in z.items():
    v=np.array(vv);rows.append(dict(case=path.parent.parent.name,offset=int(path.parent.name.split('_')[1]),process=process,block=block,label=label,gpu=float(np.median(v[:,0])),host=float(np.median(v[:,1])),requests=len(v)))
 return rows
def run(phase):
 rows=cells(phase);results=[];cases=sorted({x['case'] for x in rows})
 for metric in ['gpu','host']:
  for a,b in [('MINIMAX',b) for b in ['FAST','NATIVE','TORCH','IDENTITY','RANDOM','WORST','MINSUM','WRONG_ADDRESS']]+[('IDENTITY','FAST'),('NATIVE','TORCH'),('ANCHOR_B','ANCHOR_A'),('FAST','ANCHOR_A')]:
   v=logs(rows,a,b,metric)
   for case in ['ALL']+cases:
    values=v if case=='ALL' else [x for x in v if x['case']==case];results.append(dict(case=case,comparison=a+'/'+b,metric=metric,**summary(values)))
 write(ROOT/f'derived/soft_{phase}.json',dict(results=results,cells=rows))
 if phase=='dev' and '--freeze' in sys.argv:
  assert len({x['process'] for x in rows})==2;p=ROOT/'freeze/SOFTMAX_BASELINE.json';assert not p.exists()
  chosen={c:('NATIVE' if np.mean([x['log_ratio'] for x in logs(rows,'NATIVE','TORCH') if x['case']==c])<0 else 'TORCH') for c in cases}
  write(p,dict(created_utc=utc(),cases=chosen,rule='Choose fastest ordinary kernel only. MINIMAX map unchanged and chosen solely on independent isolated training.',development_sha256=sha(ROOT/'derived/soft_dev.json')))
 for x in results:
  if x['metric']=='gpu' and x['comparison'] in ['MINIMAX/FAST','MINIMAX/IDENTITY','MINIMAX/RANDOM','MINIMAX/WORST','NATIVE/TORCH']:print(x['case'],x['comparison'],round(x['gain_pct'],4),x['ci95_pct'])
if __name__=='__main__':run(sys.argv[1])
