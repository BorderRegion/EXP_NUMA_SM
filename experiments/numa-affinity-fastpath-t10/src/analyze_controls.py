from analyze import logs,summary
from analyze_softmax import cells
from common import *
import numpy as np,collections,sys
def run(phase):
 rows=cells(phase);results=[];cases=sorted({x['case'] for x in rows})
 if phase in ['panel','batch']:
  z=collections.defaultdict(list)
  for x in rows:
   if x['label'].startswith('RND'):z[x['case'],x['offset'],x['process'],x['block']].append(x)
  for key,a in z.items():
   assert len(a)==12
   rows.append(dict(case=key[0],offset=key[1],process=key[2],block=key[3],label='RANDOM_POOL',gpu=float(np.exp(np.mean(np.log([v['gpu'] for v in a])))),host=float(np.exp(np.mean(np.log([v['host'] for v in a])))),requests=sum(v['requests'] for v in a)))
 controls=['NATIVE','IDENTITY','WRONG_ADDRESS','RANDOM_POOL','WORST'] if phase in ['panel','batch'] else ['NATIVE','IDENTITY','WRONG_ADDRESS','RANDOM']
 if phase=='common':controls+=['WORST']
 for metric in ['gpu','host']:
  for b in controls:
   v=logs(rows,'MINIMAX',b,metric)
   for c in ['ALL']+cases:
    vv=v if c=='ALL' else [x for x in v if x['case']==c];results.append(dict(case=c,comparison='MINIMAX/'+b,metric=metric,**summary(vv)))
 by_address=[]
 for page in [0,17,257]:
  for b in controls:
   v=logs([x for x in rows if x['offset']==page],'MINIMAX',b)
   for c in ['ALL']+cases:
    vv=v if c=='ALL' else [x for x in v if x['case']==c];by_address.append(dict(address=page,case=c,comparison='MINIMAX/'+b,metric='gpu',**summary(vv)))
 write(ROOT/f'derived/soft_{phase}.json',dict(results=results,by_address_results=by_address,cells=rows))
 for x in results:
  if x['metric']=='gpu':print(x['case'],x['comparison'],round(x['gain_pct'],4),x['ci95_pct'])
 if phase=='panel':
  mapping=read(ROOT/'freeze/SOFTMAX_MAPS.json')['maps']+read(ROOT/'freeze/PANEL_PROTOCOL.json')['maps'];cost={(m['page'],m['policy']):m.get('training_mean_cycles',m.get('predicted_mean_cycles')) for m in mapping};cc=[]
  for case in cases:
   for page in [0,17,257]:
    table=[]
    for policy in ['MINIMAX','IDENTITY','WORST']+[f'RND{i:02d}' for i in range(12)]:
     tt=[x['gpu'] for x in rows if x['case']==case and x['offset']==page and x['label']==policy];table.append(dict(policy=policy,predicted_mean_cycles=cost[page,policy],observed_us=float(np.exp(np.mean(np.log(tt))))))
    cc.append(dict(case=case,page=page,cost_to_runtime_pearson=float(np.corrcoef([[x['predicted_mean_cycles'] for x in table],[x['observed_us'] for x in table]])[0,1]),policies=table))
  write(ROOT/'derived/soft_cost_transfer.json',cc)
if __name__=='__main__':run(sys.argv[1])
