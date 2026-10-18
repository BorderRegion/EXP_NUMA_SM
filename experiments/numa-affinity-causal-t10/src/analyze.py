from common import *
import numpy as np,collections,csv,gzip,sys
def cells(phase):
 rows=[]
 for worker in sorted(RUN.glob(phase+'_*')):
  process=int(worker.name.rsplit('_',1)[1])
  for p in sorted(worker.glob('V*/*/*/page*/requests.csv.gz')):
   cfg=read(p.parent/'config.json');d=collections.defaultdict(list)
   with gzip.open(p,'rt') as f:
    for x in csv.DictReader(f):
     if x['phase']=='test':d[int(x['block']),x['label']].append([float(x['gpu_us']),float(x['host_us'])])
   for (block,label),values in d.items():
    v=np.median(np.array(values),axis=0);rows.append(dict(V=cfg['V'],variant=cfg['variant'],page=cfg['page'],scope=cfg['scope'],process=process,block=block,label=label,gpu=float(v[0]),host=float(v[1])))
 return rows
def key(x):return f"{x['V']}|{x['variant']}|{x['page']}|{x['scope']}"
def summary(v):
 p=np.array(v);rng=np.random.default_rng(20261018);bs=p[rng.integers(0,len(p),(30000,len(p)))].mean(axis=1);gain=lambda a:-100*np.expm1(a)
 return dict(gain_pct=float(gain(p.mean())),process_gain_pct=gain(p).tolist(),processes=len(p),ci95_pct=np.sort(gain(np.quantile(bs,[.025,.975]))).tolist(),ci996875_pct=np.sort(gain(np.quantile(bs,[.0015625,.9984375]))).tolist())
def run(phase,freeze=False):
 rows=cells(phase);groups=collections.defaultdict(list)
 for x in rows:groups[key(x)].append(x)
 if phase=='dev' and freeze:
  assert {x['process'] for x in rows}=={0,1};chosen={}
  for k,a in groups.items():
   z=collections.defaultdict(list)
   for x in a:
    if x['label'].startswith('RND'):z[x['label']].append(np.log(x['gpu']))
   scores={label:float(np.exp(np.mean(v))) for label,v in z.items()};chosen[k]=dict(policy=min(scores,key=scores.get),development_gpu_us=scores)
  p=ROOT/'freeze/SELECTION.json';assert not p.exists();write(p,dict(created_utc=utc(),choices=chosen,rule='Minimum geometric full GPU time on two development processes among12random maps percondition; confirmation data unseen',source_hashes={str(p.relative_to(ROOT)):sha(p) for w in RUN.glob('dev_*') for p in w.rglob('requests.csv.gz')}))
 selection=read(ROOT/'freeze/SELECTION.json')['choices'] if (ROOT/'freeze/SELECTION.json').exists() else {};results=[]
 for k,a in groups.items():
  buckets=collections.defaultdict(dict)
  for x in a:buckets[x['process'],x['block']][x['label']]=x
  for metric in ['gpu','host']:
   comps=['IDENTITY','POOLED','WRONG_ADDRESS','RANDOM_POOL','NATIVE']+(['RANDOM_BEST'] if selection else [])+(['BASE_IDENTITY','BASE_MINIMAX'] if a[0]['V']==131072 else [])
   for comp in comps:
    byp=collections.defaultdict(list);absp=collections.defaultdict(list)
    for (proc,b),z in buckets.items():
     if comp=='RANDOM_POOL':ctrl=float(np.exp(np.mean([np.log(z[f'RND{i:02d}'][metric]) for i in range(12)])))
     else:ctrl=z[selection[k]['policy'] if comp=='RANDOM_BEST' else comp][metric]
     byp[proc].append(np.log(z['MINIMAX'][metric]/ctrl));absp[proc].append([z['MINIMAX'][metric],ctrl])
    base={n:a[0][n] for n in ['V','variant','page','scope']};v=[np.mean(byp[i]) for i in sorted(byp)];av=np.mean([np.mean(absp[i],axis=0) for i in sorted(absp)],axis=0)
    results.append(dict(**base,metric=metric,comparison='MINIMAX/'+comp,selected_random=selection[k]['policy'] if selection else None,method_mean_us=float(av[0]),control_mean_us=float(av[1]),**summary(v)))
 write(ROOT/f'derived/{phase}.json',dict(results=results,cells=rows))
 for x in results:
  if x['V']==131072 and x['variant']=='BOTH' and x['page']==17 and x['metric']=='gpu':print(phase,x['scope'],x['comparison'],round(x['gain_pct'],3),x['ci95_pct'],flush=True)
if __name__=='__main__':run(sys.argv[1],'--freeze' in sys.argv)
