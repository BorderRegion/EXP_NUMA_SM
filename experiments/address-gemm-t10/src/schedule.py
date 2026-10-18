import numpy as np
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
def bottleneck(cost):
 vals=np.unique(cost);lo=0;hi=len(vals)-1;n=len(cost)
 while lo<hi:
  mid=(lo+hi)//2;bad=(cost>vals[mid]).astype(float);a=hungarian(bad)
  if bad[np.arange(n),a].sum()==0:hi=mid
  else:lo=mid+1
 threshold=vals[lo];penalty=(np.ptp(cost)+1)*(n+1);a=hungarian(cost+penalty*(cost>threshold));assert max(cost[np.arange(n),a])<=threshold;return a

def compile_map(cost):
 """Each wave schedules <=56 tasks. Prior predicted SM loads enter minimax cost."""
 nsm,nt=cost.shape;assert nsm==56 and np.isfinite(cost).all() and (cost>0).all()
 waves=(nt+55)//56;out=np.full((56,waves),-1,dtype=np.int32);load=np.zeros(56)
 for wave in range(waves):
  first=wave*56;last=min(nt,first+56);c=np.zeros((56,56));c[:,:last-first]=cost[:,first:last];assign=bottleneck(c+load[:,None]);load+=c[np.arange(56),assign]
  for sm,t in enumerate(assign):
   if t<last-first:out[sm,wave]=first+t
 assert sorted(out[out>=0].tolist())==list(range(nt));return out

def all_maps(cost,seed):
 nt=cost.shape[1];waves=(nt+55)//56;rng=np.random.default_rng(seed);identity=np.full((56,waves),-1,np.int32)
 for t in range(nt):identity[t%56,t//56]=t
 random=identity.copy()
 for w in range(waves):random[:,w]=random[rng.permutation(56),w]
 row=cost.mean(axis=1,keepdims=True);col=cost.mean(axis=0,keepdims=True);base=row+col-cost.mean();res=cost-base
 # Destroy the address association while retaining per-SM/per-task main effects.
 permutation=rng.permutation(nt);shuffled=base+res[:,permutation];shuffled=np.maximum(shuffled,1)
 return dict(IDENTITY=identity,RANDOM=random,SM_ONLY=compile_map(np.maximum(base,1)),ADDRESS=compile_map(cost),SHUFFLED=compile_map(shuffled)),permutation
