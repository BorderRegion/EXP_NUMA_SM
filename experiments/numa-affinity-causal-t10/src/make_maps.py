from common import *
from topology_math import hungarian
import numpy as np,time
def bottleneck(cost):
 vals=np.unique(cost);lo=0;hi=len(vals)-1;n=len(cost)
 while lo<hi:
  mid=(lo+hi)//2;bad=(cost>vals[mid]).astype(float);a=hungarian(bad)
  if bad[np.arange(n),a].sum()==0:hi=mid
  else:lo=mid+1
 penalty=(np.ptp(cost)+1)*(n+1);a=hungarian(cost+penalty*(cost>vals[lo]));assert max(cost[np.arange(n),a])<=vals[lo];return a
if __name__=='__main__':
 p=ROOT/'freeze/MAPS.json';assert not p.exists();t=time.monotonic();old=read(ROOT/'freeze/SOFTMAX_MAPS.json');maps=[x for x in old['maps'] if x['policy'] in ['MINIMAX','IDENTITY','WORST']]+read(ROOT/'freeze/PANEL_PROTOCOL.json')['maps'];a=bottleneck(np.mean(old['cost_cycles'],axis=0));mapping=np.arange(56)//2
 for i,j in enumerate(a):mapping[2*j+1]=i
 for page,wrong in zip([0,17,257],[17,257,0]):
  maps.append(dict(page=page,policy='POOLED',map=mapping.tolist()))
  m=next(x for x in maps if x['policy']=='MINIMAX' and x['page']==wrong);maps.append(dict(page=page,policy='WRONG_ADDRESS',map=m['map']))
 for m in maps:assert sorted(m['map'][1::2])==list(range(28))
 write(p,dict(created_utc=utc(),maps=maps,pooled_fit_ms=(time.monotonic()-t)*1000,source_hashes={n:sha(ROOT/'freeze'/n) for n in ['SOFTMAX_MAPS.json','PANEL_PROTOCOL.json']},selection='No new GPU timings; pooled minimax from all3previous training cost matrices'))
 print('MAPS_FROZEN')
