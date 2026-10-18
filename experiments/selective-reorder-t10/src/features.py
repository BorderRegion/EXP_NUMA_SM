from common import *
from selection_math import *
import numpy as np

def features(c,action,bins,card,scales,permuted=False):
 b=bins[bin_id(c)];recipe=b['single_recipe'] if action in ['LIB','SINGLE'] else b['split_recipe'];s=None if action=='LIB' else 1 if action=='SINGLE' else b['split_S'];bm,bn=TILES[recipe]
 shape=log_shape_features(c['M'],c['N'],c['K'],bm,bn,s);hw=[0.]*4
 if action.startswith('PC'):
  part,pi=int(action[2]),int(action[4]);rows=[]
  for r in card['representatives']:
   fs=[]
   for x in r['samples']:
    mat=np.array(x['matrix_us']);p=np.array(x['P_us']);q=np.array(x['R_us'])
    if permuted:
     perm=card['feature_identity_permutation'];mat=mat[np.ix_(perm,perm)];p=p[perm];q=q[perm]
    fs.append(pc_features(mat.tolist(),p.tolist(),q.tolist(),part,pi,0)[:3])
   a=np.array(fs);v=np.mean(a,axis=0).tolist()+[float(np.mean(np.abs(a-np.median(a,axis=0))))]
   distance=float(np.sum(((np.log2([c['M'],c['N'],c['K']])-np.log2(r['shape']))/scales)**2));rows.append((distance,r['case'],v))
  nearest=sorted(rows)[:2];w=np.array([1/max(x[0],1e-12) for x in nearest]);w=w/w.sum();hw=np.sum([weight*np.array(x[2]) for weight,x in zip(w,nearest)],axis=0).tolist()
 return shape,hw

def feature_static_card(card):
 # Export exact continuous PC features for C++ interpolation, in fixed action order.
 values=[]
 for permuted in [False,True]:
  reps=[]
  for r in card['representatives']:
   actions=[]
   for action in ACTIONS[3:]:
    fs=[]
    for x in r['samples']:
     mat=np.array(x['matrix_us']);p=np.array(x['P_us']);q=np.array(x['R_us'])
     if permuted:
      ids=card['feature_identity_permutation'];mat=mat[np.ix_(ids,ids)];p=p[ids];q=q[ids]
     fs.append(pc_features(mat.tolist(),p.tolist(),q.tolist(),int(action[2]),int(action[4]),0)[:3])
    a=np.array(fs);actions.append(np.mean(a,axis=0).tolist()+[float(np.mean(np.abs(a-np.median(a,axis=0))))])
   reps.append(actions)
  values.append(reps)
 return values
