from analysis_lib import *
def bottleneck(cost):
 vals=np.unique(cost);lo=0;hi=len(vals)-1;n=len(cost)
 while lo<hi:
  mid=(lo+hi)//2;bad=(cost>vals[mid]).astype(float);a=hungarian(bad)
  if bad[np.arange(n),a].sum()==0:hi=mid
  else:lo=mid+1
 threshold=vals[lo];penalty=(np.ptp(cost)+1)*(n+1);a=hungarian(cost+penalty*(cost>threshold));assert max(cost[np.arange(n),a])<=threshold;return a
def tensor(path):
 e,r,ids=load_worker(path);assert len(e)==4704
 v={u:np.full((2,3,28,28),np.nan) for u in ['cycles','ns']}
 for row in e:
  i=ids.index(row['src'])//2;j=ids.index(row['dst'])//2;g=[0,17,257].index(row['slot']-i);assert row['src']==ids[2*i] and row['dst']==ids[2*j+1]
  for unit in v:v[unit][row['round'],g,i,j]=r[row['record_offset']][unit]/row['steps']
 for a in v.values():assert np.isfinite(a).all()
 return v,ids
