import json,csv,pathlib,statistics,collections
from runlib import *
def main():
 rows=[]
 for line in (ROOT/'run_index.jsonl').read_text().splitlines():
  r=json.loads(line)
  if r['stage']!='E2' or r['status']!='SUCCESS':continue
  p=ROOT/r['path'];s=json.loads((p/'summary.json').read_text());c=r['config'];g=collections.defaultdict(list)
  for x in csv.DictReader(open(p/'groups.csv')):g[int(x['group'])].append(float(x['gpu_event_ms']))
  for gi,vals in g.items():rows.append(dict(run_id=r['run_id'],family=c['family'],size=c['size'],layout=c['layout'],mode=c['mode'],process_block=c['process_block'],group=gi,sms=s['groups'][gi]['sms'],tasks=s['groups'][gi]['tasks'],gpu_event_ms=statistics.mean(vals),tasks_per_ms=s['groups'][gi]['tasks']/statistics.mean(vals),cpu_ready_ms=s['mean_cpu_ready_ms']))
 with open(ROOT/'derived/t10/capacity.csv','w') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 print('capacity records',len(rows))
 rates={}
 for size in range(3):
  x=[r for r in rows if r['size']==size and r['mode']=='concurrent'];rate=[[statistics.median([r['tasks_per_ms'] for r in x if r['group']==g and r['family']==f]) for f in [0,2,3]] for g in [0,1]];rates[str(size)]=rate
 (ROOT/'derived/t10/concurrent_rates.json').write_text(json.dumps(rates,indent=2));print(rates)
if __name__=='__main__':main()
