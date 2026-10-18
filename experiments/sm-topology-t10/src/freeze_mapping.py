from common import *
from analysis_lib import *
import random,itertools,time
t=time.monotonic();rng=np.random.default_rng(20261017)
for n in range(2,7):
 for _ in range(5):
  c=rng.normal(size=(n,n));a=hungarian(c);got=c[np.arange(n),a].sum();expected=min(c[np.arange(n),p].sum() for p in itertools.permutations(range(n)))
  assert abs(got-expected)<1e-10
pairs=[];chases=[]
for b in [0,1]:
 p,c,ids=matrices(RUN/'raw'/f'matrix_{b}');pairs.append(p);chases.append(c)
 # Save unaggregated typed arrays for inspection only; raw remains source of truth.
 np.savez_compressed(RUN/f'development_arrays_{b}.npz',pair_ns=p['ns'],pair_cycles=p['cycles'],chase_ns=c['ns'],chase_cycles=c['cycles'])
cost=np.mean([p['ns'][:,1,:2].mean(axis=(0,1)) for p in pairs],axis=0)
sub=cost[::2,1::2];minimum=hungarian(sub);maximum=hungarian(-sub);randommap=list(range(28));random.Random(2026101711).shuffle(randommap)
maps={name:[[ids[2*i],ids[2*j+1]] for i,j in enumerate(assignment)] for name,assignment in [('MIN',minimum),('IDENTITY',range(28)),('RANDOM',randommap),('MAX',maximum)]}
pr=residual(np.log(cost),True);sym=-np.nan_to_num((pr+pr.T)/2);eig,vec=np.linalg.eigh(sym);order=np.argsort(vec[:,-1]);pairgroups=[sorted(ids[i] for i in order[:28]),sorted(ids[i] for i in order[28:])]
addr=np.mean([np.log(c['cycles'][:,0]).mean(axis=0) for c in chases],axis=0);ar=residual(addr);u,s,vh=np.linalg.svd(ar,full_matrices=False);coefficient=u[:,0].copy()
parity=np.array([1 if (r&0x33).bit_count()%2 else -1 for r in range(64)])
if np.dot(vh[0],parity)<0:coefficient=-coefficient
order=np.argsort(coefficient);addrgroups=[sorted(ids[i] for i in order[:28]),sorted(ids[i] for i in order[28:])]
rule=dict(frozen_at=utc(),fit_seconds=time.monotonic()-t,training_processes=[0,1],training_slots=[0,1],mode='64B_PAYLOAD',objective='Minimum sum of mean source-clock roundtrip ns; all28 producers and consumers used once',policy_order=list(maps),maps=maps,development_sum_cost_ns={name:float(sum(cost[ids.index(a),ids.index(b)] for a,b in ps)) for name,ps in maps.items()},pair_exploratory_2groups=pairgroups,address_exploratory_2groups=addrgroups,address_singular_values=s.tolist(),address_old_parity_0x33_shape_correlation=corr(vh[0],parity),test_data_seen=False,assignment_cpu_test='PASS:25 exhaustive comparisons n2..6')
write(ROOT/'freeze/MAPPING.json',rule)
text=str(len(maps))+'\n'+'\n'.join(f'{a} {b}' for ps in maps.values() for a,b in ps)+'\n';(ROOT/'plans/frozen_maps.txt').write_text(text)
for b in range(4):
 rows=[];rg=random.Random(2026101780+b)
 for steps in [128,512]:
  for policy in range(4):
   for j in range(3):rows.append([3,-1,1,0,0,0,steps,0,policy])
  for repeat in range(16):
   policies=list(range(4));rg.shuffle(policies)
   for policy in policies:rows.append([3,repeat,1,0,0,0,steps,0,policy])
 (ROOT/'plans'/f'deploy_{b}.txt').write_text('\n'.join(' '.join(map(str,r)) for r in rows)+'\n')
write(ROOT/'freeze/DEPLOY_PLAN_HASHES.json',{p.name:sha(p) for p in (ROOT/'plans').glob('*') if p.name.startswith('deploy_') or p.name=='frozen_maps.txt'})
print(json.dumps(rule,indent=2))
