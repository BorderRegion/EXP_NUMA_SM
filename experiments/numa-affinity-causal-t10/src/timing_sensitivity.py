"""Post-hoc timing-state sensitivity; original estimand/data are never replaced."""
from common import *
from analyze import summary
import numpy as np,csv,gzip,collections
def run():
 selection=read(ROOT/'freeze/SELECTION.json')['choices'];z=collections.defaultdict(dict);profiles=collections.defaultdict(list)
 for w in sorted(RUN.glob('confirm_*')):
  proc=int(w.name.split('_')[1])
  for scope in ['ready','fresh','batch','freshbatch']:
   p=w/'V131072/BOTH'/scope/'page17/requests.csv.gz';a=collections.defaultdict(dict)
   with gzip.open(p,'rt') as f:
    for x in csv.DictReader(f):
     if x['phase']=='test':a[int(x['block']),x['label']][int(x['request'])]=float(x['gpu_us'])
   for (block,policy),values in a.items():
    assert set(values)==set(range(8));den=np.median([values[i] for i in range(4,8)])
    for i in range(8):profiles[scope,i].append(values[i]/den)
    for window,indices in [('all8',range(8)),('last4',range(4,8))]:z[scope,window,proc,block][policy]=float(np.median([values[i] for i in indices]))
 result=[]
 for scope in ['ready','fresh','batch','freshbatch']:
  for window in ['all8','last4']:
   for comp in ['IDENTITY','RANDOM_BEST','POOLED','WRONG_ADDRESS','BASE_IDENTITY','BASE_MINIMAX']:
    ref=selection[f'131072|BOTH|17|{scope}']['policy'] if comp=='RANDOM_BEST' else comp;v=collections.defaultdict(list)
    for (s,win,p,b),a in z.items():
     if s==scope and win==window:v[p].append(np.log(a['MINIMAX']/a[ref]))
    result.append(dict(scope=scope,window=window,comparison='MINIMAX/'+comp,**summary([np.mean(v[p]) for p in sorted(v)])))
 primary=read(ROOT/'derived/confirm.json')['results']
 for x in result:
  if x['window']=='all8':
   p=next(p for p in primary if p['V']==131072 and p['variant']=='BOTH' and p['page']==17 and p['scope']==x['scope'] and p['metric']=='gpu' and p['comparison']==x['comparison']);assert abs(p['gain_pct']-x['gain_pct'])<1e-10
 out=dict(status='PASS',post_hoc=True,scope='Primary V131072/BOTH/page17 only; GPU timing',warning='last4 is warm-within-burst sensitivity, not cold/first-request latency and not a replacement primary outcome; all original observations preserved.',results=result,replay_profiles=[dict(scope=k[0],request=k[1],median_vs_last4=float(np.median(v)),p10=float(np.quantile(v,.1)),p90=float(np.quantile(v,.9)),observations=len(v)) for k,v in profiles.items()])
 write(ROOT/'derived/TIMING_SENSITIVITY.json',out);return out
if __name__=='__main__':
 x=run()
 for v in x['results']:
  if v['window']=='last4' and v['comparison'] in ['MINIMAX/IDENTITY','MINIMAX/BASE_IDENTITY']:print(v['scope'],v['comparison'],v['gain_pct'],v['ci95_pct'])
