from common import *
import gzip,csv,numpy as np,collections
def load(path):
 with gzip.open(path,'rt') as f:rows=list(csv.DictReader(f))
 groups=collections.defaultdict(list)
 for r in rows:
  if r['phase']=='test':groups[int(r['block']),r['label']].append(r)
 return rows,{k:{m:float(np.median([float(r[m]) for r in a])) for m in ['gpu_us','host_us']} for k,a in groups.items()}
def compute():
 prot=read(ROOT/'freeze/PROTOCOL.json');result={}
 for c in prot['cases']:
  scores=collections.defaultdict(list);cfg=None
  for p in range(2):
   for offset in prot['offsets_bytes']:
    path=RUN/f'development_{p}'/c['id']/f'offset_{offset}';_,g=load(path/'requests.csv.gz');cfg=read(path/'configs.json')
    for name in cfg:
     for b in range(10):scores[name].append(np.log(g[b,name]['gpu_us']/g[b,'LEGACY']['gpu_us']))
  scores={k:float(np.mean(v)) for k,v in scores.items()}
  best=lambda labels:min(labels,key=lambda x:(scores[x],x))
  stat=best([n for n in cfg if cfg[n]['mode'] in [0,10,11] and not cfg[n].get('legacy')]);coarse=best([n for n in cfg if cfg[n]['mode']==1 and not cfg[n].get('legacy')]);rep=best([n for n in cfg if cfg[n]['mode']==5])
  candidates={'STATIC':stat,'COARSE_BLIND':coarse,'COARSE_MATCH':coarse.replace('M1_','M2_'),'REPLICA_BLIND':rep,'REPLICA_MATCH':rep.replace('M5_','M6_')}
  route=min(candidates,key=lambda x:(scores[candidates[x]],x))
  result[c['id']]=dict(static=cfg[stat],coarse=cfg[coarse],replica=cfg[rep],route=route,source_labels=candidates,development_log_ratios=scores)
 return dict(cases=result,selection_rule='Static/queue/replica geometry selected on development. Queue and replica geometry selected by blind control, direction MATCH fixed a priori; final best candidate frozen before confirmation.')
if __name__=='__main__':x=compute();x['frozen_utc']=utc();write(ROOT/'freeze/SELECTION.json',x);print(json.dumps({k:{a:v[a] for a in ['static','coarse','replica','route']} for k,v in x['cases'].items()},indent=2))
