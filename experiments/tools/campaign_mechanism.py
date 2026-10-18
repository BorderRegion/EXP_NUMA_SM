import sys,random,numpy as np
from runlib import *
sys.path.insert(0,str(ROOT/'GPU_COMPUTE_TOPOLOGY_DUAL_20261014/tools'))
from reference import static_minimax,quotas
def main():
 rates=json.loads((ROOT/'derived/t10/concurrent_rates.json').read_text())['1'];sms=[18,38];base=ROOT/'preregistration/E3';base.mkdir(exist_ok=True)
 # Native, blind, space, load, single-rate, typed, permuted; T is unavailable.
 policies=['N','I','S','L','R','M','P'];specs=[]
 for dist in range(3):
  for load in range(2):
   n=[1024,4096][load];types=[i%3 if dist==0 else min(2,3*i//n) if dist==1 else (0 if i%8==0 else 1 if i%8<4 else 2) for i in range(n)];units=[256,64,1];weights=[1.0 for _ in types];families=[0,2,3]
   p=base/f'd{dist}_l{load}';p.mkdir(exist_ok=True);(p/'tasks.txt').write_text(''.join(f'{families[c]} {units[c]}\n' for c in types))
   # work in calibrated task equivalents; compute, cache and streaming rates
   # all represent the identical nominal body used in E2.
   single=[3/sum(1/r for r in rr) for rr in rates]
   maps={};q=quotas(n,sms);maps['S']=[0]*q[0]+[1]*q[1];order=list(range(n));random.Random(2026101401).shuffle(order);maps['I']=[0]*n
   for j,t in enumerate(order):maps['I'][t]=0 if j<q[0] else 1
   task_cost=[sum(1/rates[g][c] for g in range(2))/2 for c in types]
   maps['L']=static_minimax([[w/s for s in sms] for w in task_cost]);maps['R']=static_minimax([[w/s for s in single] for w in task_cost]);maps['M']=static_minimax([[1/rates[g][c] for g in range(2)] for c in types])
   # Permute per-SM type rates, retain actual quota and complete task set.
   maps['P']=static_minimax([[1/(rates[1-g][c]/sms[1-g]*sms[g]) for g in range(2)] for c in types])
   for policy,m in maps.items():(p/f'{policy}.txt').write_text('\n'.join(map(str,m)))
   card=dict(rates=rates,sms=sms,types=types,task_cost=task_cost,plan_overlap_M_R=sum(x==y for x,y in zip(maps['M'],maps['R']))/n,policies=policies)
   (p/'plan_card.json').write_text(json.dumps(card,indent=2))
   for block in range(6):
    middle=policies[1:];random.Random(2026101402+dist*100+load*10+block).shuffle(middle)
    for policy in ['N']+middle:specs.append(dict(distribution=dist,load=load,block=block,policy=policy,tasks=n,plan_dir=str(p.relative_to(ROOT))))
 (base/'sessions.json').write_text(json.dumps(specs,indent=2));decision('D006','E3 frozen: 3 distributions x 2 loads x 7 policies x 6 independent process blocks. Each policy launched as a fresh process within randomized paired batch; does not share allocations across policy processes; disclose this difference from ideal shared-process application blocks. T unavailable. No parameters selected on E3 timings.')
 for c in specs:
  p=ROOT/c['plan_dir'];args=['--family',-1,'--size',1,'--tasks',c['tasks'],'--mode','native' if c['policy']=='N' else 'concurrent','--layout',2,'--task-file',str(p/'tasks.txt')]
  if c['policy']!='N':args+=['--plan',str(p/(c['policy']+'.txt'))]
  path,m=run('E3',c,args)
  if m['status']!='SUCCESS':raise RuntimeError(path)
if __name__=='__main__':main()
