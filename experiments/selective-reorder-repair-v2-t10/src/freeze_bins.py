from common import *
import math,statistics
cases={c['id']:c for c in read(INPUT/'plans/cases.json') if c['split']=='development'}
rows=sum([lines(worker_dir(f'S2_base_{b}')/'phases.jsonl') for b in range(2)],[]);assert len(rows)==720
result={};cards=[]
for bid in sorted({bin_id(c) for c in cases.values()}):
 selected=[r for r in rows if bin_id(cases[r['case']])==bid and r['action']!='LIB'];scores={}
 for recipe in [0,2,3]:
  for s in [1,2,4,8]:
   values=[r['cpu_ready_us'] for r in selected if r['recipe']==recipe and r['S']==s];assert values
   scores[recipe,s]=statistics.mean(math.log(v) for v in values)
 single=min([(r,1) for r in [0,2,3]],key=scores.get);split=min([(r,s) for r in [0,2,3] for s in [2,4,8]],key=scores.get)
 result[bid]=dict(single_recipe=single[0],split_recipe=split[0],split_S=split[1],n_development_cases=len({r['case'] for r in selected}),scores=[dict(recipe=r,S=s,geomean_cpu_us=math.exp(v)) for (r,s),v in scores.items()])
assert not (ROOT/'freeze/bins.json').exists();write(ROOT/'freeze/bins.json',result);print(result)
