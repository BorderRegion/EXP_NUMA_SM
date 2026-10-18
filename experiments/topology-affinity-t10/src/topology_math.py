from pathlib import Path
import csv,json,numpy as np
DT=np.dtype([(k,'<u8') for k in ['ns','cycles','peer_ns','peer_cycles']]+[(k,'<u4') for k in ['src_begin','src_end','dst_begin','dst_end','errors','src_value','dst_value','reserved']]+[('roster_begin','<u2',(56,)),('roster_end','<u2',(56,))])
assert DT.itemsize==288
def load_worker(path):
 e=np.genfromtxt(path/'epochs.csv',delimiter=',',names=True,dtype=None,encoding=None)
 e=np.atleast_1d(e);r=np.fromfile(path/'records.bin',dtype=DT)
 ids=json.loads((path/'environment.json').read_text())['roster']
 assert int(e['record_count'].sum())==len(r)
 assert np.all(r['errors']==0) and np.all(r['src_begin']==r['src_end'])
 first=r[e['record_offset']]
 assert np.all(np.sort(first['roster_begin'],axis=1)==ids)
 assert np.array_equal(first['roster_begin'],first['roster_end'])
 return e,r,ids
def matrices(path):
 e,r,ids=load_worker(path);ix={s:i for i,s in enumerate(ids)}
 pair={k:np.full((2,2,3,56,56),np.nan) for k in ['ns','cycles']}
 chase={k:np.full((2,2,56,64),np.nan) for k in ['ns','cycles']}
 for row in e:
  v=r[row['record_offset']];idx=(row['round'],row['mode'],row['slot'],ix[row['src']],ix[row['dst']]) if row['kind']==1 else (row['round'],row['mode'],ix[row['src']],row['region'])
  for unit in ['ns','cycles']:(pair if row['kind']==1 else chase)[unit][idx]=v[unit]/row['steps']
 for d in [pair,chase]:
  for v in d.values():assert np.isfinite(v).all() and (v>0).all()
 return pair,chase,ids
def residual(x,diagonal=False):
 y=np.array(x,dtype=float,copy=True)
 if diagonal:np.fill_diagonal(y,np.nan)
 for _ in range(20):
  y-=np.nanmean(y,axis=1,keepdims=True);y-=np.nanmean(y,axis=0,keepdims=True)
 return y
def corr(a,b):
 a=np.ravel(a);b=np.ravel(b);mask=np.isfinite(a)&np.isfinite(b)
 return float(np.corrcoef(a[mask],b[mask])[0,1])
def hungarian(cost):
 # Exact O(n^3) primal-dual assignment; independently verified against exhaustive small problems.
 cost=np.asarray(cost,float);n,m=cost.shape;assert n<=m
 u=np.zeros(n+1);v=np.zeros(m+1);p=np.zeros(m+1,dtype=int);way=np.zeros(m+1,dtype=int)
 for i in range(1,n+1):
  p[0]=i;j0=0;minimum=np.full(m+1,np.inf);used=np.zeros(m+1,dtype=bool)
  while True:
   used[j0]=True;i0=p[j0];delta=np.inf;j1=0
   for j in range(1,m+1):
    if not used[j]:
     cur=cost[i0-1,j-1]-u[i0]-v[j]
     if cur<minimum[j]:minimum[j]=cur;way[j]=j0
     if minimum[j]<delta:delta=minimum[j];j1=j
   for j in range(m+1):
    if used[j]:u[p[j]]+=delta;v[j]-=delta
    else:minimum[j]-=delta
   j0=j1
   if p[j0]==0:break
  while True:
   j1=way[j0];p[j0]=p[j1];j0=j1
   if j0==0:break
 answer=np.empty(n,dtype=int)
 for j in range(1,m+1):
  if p[j]:answer[p[j]-1]=j-1
 return answer
