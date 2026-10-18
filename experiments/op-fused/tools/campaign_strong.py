"""Six process blocks per fixed native-library cohort; no candidate claims."""
import json,math,hashlib,datetime
from worker import ROOT,run

def freeze():
 path=ROOT/'preregistration/strong_library_freeze.json'
 if path.exists():return
 logs={}
 for line in (ROOT/'registry/runs.jsonl').read_text().splitlines():
  m=json.loads(line)
  if not m['key'].startswith('E1_strong_block_'):continue
  for p in (ROOT/m['path']).glob('grouped-*.json'):
   x=json.loads(p.read_text())
   if x['status']!='STRONG_LIBRARY_BASELINE_ONLY':continue
   means={y['variant']:y['device_interval_ms'] for y in x['phases'] if y['phase_role']=='primary'}
   logs.setdefault(x['case']['case_id'],[]).append(math.log(means['NATIVE_GROUPED_GRAPH']/means['PER_EXPERT_GRAPH']))
 assert len(logs)==24 and all(5<=len(v)<=6 for v in logs.values())
 ratio=math.exp(sum(sum(v)/len(v) for v in logs.values())/len(logs))
 path.write_text(json.dumps(dict(frozen_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),selected='NATIVE_GROUPED_GRAPH' if ratio<1 else 'PER_EXPERT_GRAPH',criterion='E1 24cases equal-case geometric mean; six process attempts, actual five/six valid blocks after retained instrumentation failures; no holdout lookup',native_over_per_expert=ratio,case_counts={k:len(v) for k,v in logs.items()},cohort_sha256=hashlib.sha256((ROOT/'preregistration/strong_library_cohort.json').read_bytes()).hexdigest(),candidate=None),indent=2))

if __name__=='__main__':
 q=run('E0','native_grouped_zero_edge_audit_repair_qualification',ROOT/'tools/strong_bench.py',['--qualify'])
 assert q['status']=='COMPLETED'
 assert json.loads((ROOT/q['path']/'qualification.json').read_text())['status']=='SUPPORTED_NUMERICAL_AND_GRAPH'
 for stage in ['E1','E3','E4']:
  if stage!='E1':freeze()
  for b in range(6):
   m=run(stage,f'{stage}_strong_block_{b}',ROOT/'tools/strong_bench.py',['--stage',stage,'--block',b])
   assert m['status']=='COMPLETED',m['key']
  if stage=='E1':freeze()
