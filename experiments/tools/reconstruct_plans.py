"""Post-run CPU reconstruction only. Never substitutes for original build timing."""
import json,pathlib,time,csv,sys,statistics
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'GPU_COMPUTE_TOPOLOGY_DUAL_20261014/tools'));from reference import static_minimax
rows=[]
for card in sorted((ROOT/'preregistration').glob('W*/*/plan_card.json')):
 d=json.loads(card.read_text());w=json.loads((card.parent/'weights.json').read_text());rates=d['rates'];single=d['single_rate']
 for pol in 'RM':
  expected=list(map(int,(card.parent/(pol+'.txt')).read_text().split()))
  for repeat in range(3):
   start=time.perf_counter();costs=[[x/rates[g][cl]for g in range(2)]for x,cl in zip(w['weights'],w['classes'])]if pol=='M'else[[x/s for s in single]for x in w['weights']];mapping=static_minimax(costs);elapsed=(time.perf_counter()-start)*1000;assert mapping==expected
   rows.append(dict(workload=card.parts[-3],input=card.parent.name,policy=pol,repeat=repeat,tasks=len(mapping),reconstruction_ms=elapsed,exact_map_match=True,scope='post-run CPU reconstruction; original planning wall time unknown'))
with open(ROOT/'derived/t10/plan_reconstruction.csv','w')as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
print('All 24 reconstruction maps match frozen plans; times are post-run measurements only.')
