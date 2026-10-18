from common import *
import csv,gzip,collections,numpy as np

def load(path):
 rows=list(csv.DictReader(gzip.open(path,'rt')));g=collections.defaultdict(list)
 for r in rows:g[r['phase'],int(r['block']),r['label']].append(r)
 return rows,{key:{m:float(np.median([float(r[m]) for r in rr])) for m in ['gpu_us','host_us']} for key,rr in g.items()}
def compute():
 scores=collections.defaultdict(lambda:collections.defaultdict(list));qscore=collections.defaultdict(lambda:collections.defaultdict(list))
 for proc in range(2):
  for p in sorted((RUN/f'development_{proc}').glob('*/*/requests.csv.gz')):
   rows,g=load(p);cid=rows[0]['case'];conf=read(p.parent/'configs.json');condition={}
   for name in conf:
    val=float(np.mean([np.log(g['test',b,name]['gpu_us']/g['test',b,'BMM_IDEAL']['gpu_us']) for b in range(12)]));scores[cid][name].append(val);condition[name]=val
   for W in [8,16,32,64,128]:
    for f in [0,1]:qscore[cid][(W,f)].append(min(condition[f'MATCH_W{W}_F{f}'],condition[f'INVERT_W{W}_F{f}']))
 result={}
 for cid,v in scores.items():
  x={name:float(np.exp(np.mean(a))) for name,a in v.items()};direct=min([n for n in x if n.startswith('DIRECT') and n.endswith('F0')],key=lambda n:(x[n],n));fused=min([n for n in x if n.startswith('DIRECT') and n.endswith('F1')],key=lambda n:(x[n],n));queue=min(qscore[cid],key=lambda n:(np.mean(qscore[cid][n]),n));library=min(['BMM_IDEAL','SDPA_VIEW_IDEAL'],key=lambda n:(x[n],n));best_custom='DIRECT' if x[direct]<=x[fused] else 'FUSED';bestscore=min(x[direct],x[fused]);route=best_custom if bestscore<x[library] else library
  result[cid]=dict(direct=int(direct.split('_W')[1].split('_')[0]),fused=int(fused.split('_W')[1].split('_')[0]),queue=list(queue),library=library,best_custom=best_custom,route=route,scores_vs_BMM=x,queue_scores={str(k):float(np.exp(np.mean(a))) for k,a in qscore[cid].items()})
 return dict(cases=result,protocol_sha256=sha(ROOT/'freeze/PROTOCOL.json'),scope='Development only; custom/library route frozen before confirmation; no address calibration cost hidden')
if __name__=='__main__':x=compute();x['frozen_utc']=utc();write(ROOT/'freeze/SELECTION.json',x);print(json.dumps(x,indent=2))
