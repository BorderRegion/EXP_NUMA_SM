from common import *
from topology_math import *
import random,time
from worker import run
def bottleneck(cost):
 vals=np.unique(cost);lo=0;hi=len(vals)-1;n=len(cost)
 while lo<hi:
  mid=(lo+hi)//2;bad=(cost>vals[mid]).astype(float);a=hungarian(bad)
  if bad[np.arange(n),a].sum()==0:hi=mid
  else:lo=mid+1
 penalty=(np.ptp(cost)+1)*(n+1);a=hungarian(cost+penalty*(cost>vals[lo]));assert max(cost[np.arange(n),a])<=vals[lo];return a
def tensor(path):
 e,r,ids=load_worker(path);assert ids==list(range(56));a=np.full((2,3,28,28),np.nan)
 for x in e:
  i=x['src']//2;j=x['dst']//2;g=[0,17,257].index(x['slot']-i);a[x['round'],g,i,j]=r[x['record_offset']]['cycles']/x['steps']
 assert np.isfinite(a).all();return a
def main():
 for n in range(4):
  rows=[];rng=random.Random(103000000+n)
  for rnd in range(2):
   subset=[[1,rnd,1,page+i,2*i,2*j+1,128,0,0] for page in [0,17,257] for i in range(28) for j in range(28)];rng.shuffle(subset);rows.extend(subset)
  p=ROOT/f'plans/soft_tensor_{n}.txt';p.write_text('\n'.join(' '.join(map(str,x)) for x in rows)+'\n')
 write(ROOT/'freeze/SOFTMAX_CALIBRATION_EXECUTION.json',dict(created_utc=utc(),hashes={str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'src/probe8.cu',ROOT/'src/probe8_runner.cpp',ROOT/'src/types.hpp',ROOT/'build/probe8.cubin',ROOT/'build/probe8_runner']+list((ROOT/'plans').glob('soft_tensor*'))}))
 for n in range(2):run(f'soft_tensor_{n}',[ROOT/'build/probe8_runner','--cubin',ROOT/'build/probe8.cubin','--plan',ROOT/f'plans/soft_tensor_{n}.txt','--out','{OUT}'])
 cost=np.mean([tensor(RUN/f'soft_tensor_{n}') for n in range(2)],axis=(0,1));maps=[];t=time.monotonic()
 for g,page in enumerate([0,17,257]):
  permutations={'MINIMAX':bottleneck(cost[g]),'MINSUM':hungarian(cost[g]),'WORST':hungarian(-cost[g]),'IDENTITY':np.arange(28),'RANDOM':np.random.default_rng(103500000+g).permutation(28)}
  for name,perm in permutations.items():
   mapping=np.arange(56)//2
   for i,j in enumerate(perm):mapping[2*j+1]=i
   maps.append(dict(page=page,policy=name,consumer_per_producer=(2*perm+1).tolist(),map=mapping.tolist(),training_mean_cycles=float(cost[g,np.arange(28),perm].mean()),training_max_cycles=float(cost[g,np.arange(28),perm].max())))
 write(ROOT/'freeze/SOFTMAX_MAPS.json',dict(created_utc=utc(),source_workers=['soft_tensor_0','soft_tensor_1'],source_hashes={str(RUN/f'soft_tensor_{n}/records.bin'):sha(RUN/f'soft_tensor_{n}/records.bin') for n in range(2)},cost_cycles=cost.tolist(),maps=maps,fit_ms=(time.monotonic()-t)*1000))
 for n in range(2,4):run(f'soft_tensor_{n}',[ROOT/'build/probe8_runner','--cubin',ROOT/'build/probe8.cubin','--plan',ROOT/f'plans/soft_tensor_{n}.txt','--out','{OUT}'])
 confirm=np.mean([tensor(RUN/f'soft_tensor_{n}') for n in [2,3]],axis=(0,1));audit=[]
 for g,page in enumerate([0,17,257]):
  audit.append(dict(page=page,residual_correlation=corr(residual(cost[g]),residual(confirm[g])),training=cost[g].tolist(),confirmation=confirm[g].tolist(),policy=[dict(policy=m['policy'],confirmation_mean_cycles=float(confirm[g,np.arange(28),(np.array(m['consumer_per_producer'])-1)//2].mean()),confirmation_max_cycles=float(confirm[g,np.arange(28),(np.array(m['consumer_per_producer'])-1)//2].max())) for m in maps if m['page']==page]))
 write(ROOT/'derived/softmax_topology.json',audit)
 print('CALIBRATION_COMPLETE',[(x['page'],x['residual_correlation']) for x in audit])
if __name__=='__main__':main()
