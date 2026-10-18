from common import *
import numpy as np,sys
sys.path.insert(0,str(ROOT/'reference'))
from relative_policy import additive_features,PARTS
card=read(ROOT/'freeze/RESOURCE_CARD.json');ids=[2,0,3,1];inv=np.argsort(ids);errors=[];features=[]
for rep in card['representatives']:
 for part in range(3):
  for pi in range(2):
   before=[];after=[];g=[[int(inv[i]) for i in side] for side in PARTS[part]]
   for raw in rep['samples']:
    old=np.array(additive_features(raw,part,pi));t=np.array(raw['matrix_us'])[np.ix_(ids,ids)];p=np.array(raw['P_us'])[ids];r=np.array(raw['R_us'])[ids];res=t-t.mean(1)[:,None]-t.mean(0)[None,:]+t.mean()
    def imbalance(v):
     caps=[sum(1/v[i] for i in side) for side in g];return abs(caps[0]-caps[1])/sum(caps)
    new=np.array([imbalance(p),imbalance(r),np.mean([res[i,j] for b in [0,1] for i in g[b] for j in g[b^pi]])/t.mean()]);errors.append(float(np.max(np.abs(old-new))));before.append(old);after.append(new)
   def aggregate(x):
    a=np.array(x);return np.append(a.mean(0),np.mean(np.abs(a-np.median(a,axis=0))))
   delta=float(np.max(np.abs(aggregate(before)-aggregate(after))));assert delta<1e-12;features.append(dict(case=rep['case'],part=part,pi=pi,max_error=delta))
assert max(errors)<1e-12
write(ROOT/'reports/CONSISTENT_RENAMING_V2.json',dict(status='PASS',sample_feature_checks=len(errors),aggregate_four_feature_checks=len(features),max_sample_error=max(errors),max_aggregate_error=max(x['max_error'] for x in features),rows=features,scope='Simultaneously relabel card rows/columns/capacities and actual partition membership. All four RESOURCE features invariant; applying unchanged ridge coefficients therefore preserves predictions within floating arithmetic. No GPU intervention or physical identity proof.'))
print('RENAMING_INVARIANCE_PASS',len(errors),len(features))
