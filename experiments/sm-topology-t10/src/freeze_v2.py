from common import *
from analysis_lib import *
import itertools,random,shutil,subprocess,time
def bottleneck(cost):
 vals=np.unique(cost);lo=0;hi=len(vals)-1
 while lo<hi:
  mid=(lo+hi)//2;bad=(cost>vals[mid]).astype(float);assignment=hungarian(bad)
  if bad[np.arange(len(cost)),assignment].sum()==0:hi=mid
  else:lo=mid+1
 threshold=vals[lo];penalty=(np.ptp(cost)+1)*(len(cost)+1)
 assignment=hungarian(cost+penalty*(cost>threshold))
 assert np.max(cost[np.arange(len(cost)),assignment])<=threshold
 return assignment
rg=np.random.default_rng(117)
for n in range(2,7):
 for _ in range(5):
  c=rg.normal(size=(n,n));p=bottleneck(c);got=(max(c[np.arange(n),p]),sum(c[np.arange(n),p]));best=min((max(c[np.arange(n),q]),sum(c[np.arange(n),q])) for q in itertools.permutations(range(n)))
  assert np.allclose(got,best,rtol=0,atol=1e-10)
t=time.monotonic();p=[]
for b in [0,1]:
 a,c,ids=matrices(RUN/'raw'/f'matrix_{b}');p.append(a)
cost=np.mean([a['cycles'][:,1,:2].mean(axis=(0,1)) for a in p],axis=0);sub=cost[::2,1::2]
old=json.loads((ROOT/'freeze/MAPPING.json').read_text());maps={'OLD_NS_SUM':old['maps']['MIN']}
for name,perm in [('CYCLE_SUM',hungarian(sub)),('CYCLE_MAX',bottleneck(sub))]:maps[name]=[[ids[2*i],ids[2*j+1]] for i,j in enumerate(perm)]
maps['IDENTITY']=old['maps']['IDENTITY'];maps['RANDOM']=old['maps']['RANDOM']
lr=residual(np.log(cost),True);profiles=np.concatenate([np.nan_to_num(lr),np.nan_to_num(lr.T)],axis=1);u,s,vh=np.linalg.svd(profiles,full_matrices=False);order=np.argsort(u[:,0]);rank=np.argsort(np.argsort(lr,axis=1),axis=1)
edges=[]
for i in range(56):
 for j in range(i+1,56):
  if rank[i,j]<3 and rank[j,i]<3:edges.append([ids[i],ids[j]])
protocol=dict(frozen_at=utc(),status='V2_FROZEN_BEFORE_NEW_CONFIRMATION',motivation='V1 mean-ns assignment failed under simultaneous28-pair traffic. Cycle shape replicated, but frequency polluted ns fitting and sum is not parallel makespan. Explicit adaptive second stage; v1 negatives retained.',fit_processes=[0,1],fit_slots=[0,1],heldout_matrix_processes=[4,5],new_deployment_processes=list(range(6)),maps=maps,policy_order=list(maps),objective='CYCLE_SUM: min sum; CYCLE_MAX: min maximum isolated pair RTT cycles, min sum breaks ties. Predictive heuristic for concurrent makespan, not a proof.',slot_offsets_bytes=[0,17*4096,257*4096],concurrent_steps=[128,512],repeats=12,warm_launches_each_condition=3,primary_comparisons=['CYCLE_MAX vs IDENTITY','CYCLE_MAX vs RANDOM'],secondary_comparisons=['CYCLE_MAX vs CYCLE_SUM','CYCLE_MAX vs OLD_NS_SUM'],raw_allocation='Per-pair flags at base+slot_offset+4096*pair_id, independent directions at+0/+128 and64B payload at+256',learned_diagnostic_plot_order=[ids[i] for i in order],mutual_top3_residual_edges=edges,source_clock_costs={name:dict(mean=float(np.mean([cost[ids.index(a),ids.index(b)] for a,b in ps])),maximum=float(np.max([cost[ids.index(a),ids.index(b)] for a,b in ps]))) for name,ps in maps.items()},assignment_test='PASS:25 exhaustive bottleneck+sum comparisons',fit_seconds=time.monotonic()-t,inference_limit='Adaptive after v1, new stages are independent verification of v2 only. No hardware distance claim or application deployment claim.')
write(ROOT/'freeze/PROTOCOL_V2.json',protocol)
(ROOT/'plans/frozen_maps_v2.txt').write_text(str(len(maps))+'\n'+'\n'.join(f'{a} {b}' for ps in maps.values() for a,b in ps)+'\n')
for b in [4,5]:
 rows=[];rng=random.Random(2026101700+b)
 for rnd in range(2):
  subrows=[[1,rnd,mode,slot,s,d,128,0,0] for mode in [0,1] for slot in range(3) for s in ids for d in ids]
  subrows += [[2,rnd,mode,0,s,0,1024,r,0] for mode in [0,1] for s in ids for r in range(64)]
  rng.shuffle(subrows);rows+=subrows
 (ROOT/'plans'/f'matrix_{b}.txt').write_text('\n'.join(' '.join(map(str,x)) for x in rows)+'\n')
for b in range(6):
 rows=[];rng=random.Random(2026101790+b);conditions=[(n,s) for n in [128,512] for s in range(3)];rng.shuffle(conditions)
 for n,s in conditions:
  order=list(range(5));rng.shuffle(order)
  for policy in order:
   for j in range(3):rows.append([3,-1,1,s,0,0,n,0,policy])
  for rnd in range(12):
   order=list(range(5));rng.shuffle(order)
   for policy in order:rows.append([3,rnd,1,s,0,0,n,0,policy])
 (ROOT/'plans'/f'deploy_v2_{b}.txt').write_text('\n'.join(' '.join(map(str,x)) for x in rows)+'\n')
qual=[[3,0,1,s,0,0,n,0,p] for s in range(3) for n in [128,512] for p in range(5)]
(ROOT/'plans/qualification_v2.txt').write_text('\n'.join(' '.join(map(str,x)) for x in qual)+'\n')
write(ROOT/'freeze/V2_PLAN_HASHES.json',{p.name:sha(p) for p in (ROOT/'plans').glob('*') if 'v2' in p.name or p.name in ['matrix_4.txt','matrix_5.txt']})
print(json.dumps(protocol,indent=2))
