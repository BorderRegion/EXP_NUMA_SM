"""Finite resource-limited native campaign. Does not invent missing candidate cells."""
import json,pathlib,sys,statistics,math
from worker import ROOT,run
def block(stage,b,only=None):
 args=['--stage',stage,'--block',b]
 if only:args+=['--only',','.join(only)]
 m=run(stage,stage+'_native_block_'+str(b),ROOT/'tools/native_bench.py',args)
 if m['status']!='COMPLETED':raise SystemExit('Worker failed: '+m['key'])
 return m
def freeze():
 out=ROOT/'preregistration/library_freeze.json'
 if out.exists():return
 ratios=[];cases={};fail=[]
 for m in [json.loads(x) for x in (ROOT/'registry/runs.jsonl').read_text().splitlines()]:
  if not m['key'].startswith('E1_native_block_'):continue
  for p in (ROOT/m['path']).glob('*.json'):
   x=json.loads(p.read_text())
   if 'case' not in x:continue
   if x['status']!='BASELINE_ONLY':fail.append([x['case']['case_id'],x['status']]);continue
   if x['case']['suite']!='grouped':continue
   d={r['variant']:r['device_interval_ms'] for r in x['phases'] if r['phase_role']=='primary'}
   if 'CUBLAS_GRAPH' in d and 'CUBLASLT_GRAPH' in d:cases.setdefault(x['case']['case_id'],[]).append(math.log(d['CUBLASLT_GRAPH']/d['CUBLAS_GRAPH']))
 for k,v in cases.items():ratios.append(sum(v)/len(v))
 ratio=math.exp(sum(ratios)/len(ratios))
 out.write_text(json.dumps(dict(selected='cublaslt' if ratio<1 else 'cublas',criterion='equal-case geometric mean over the 24 grouped calibration cases only; dense/heterogeneous controls excluded',cublaslt_over_cublas=ratio,case_count=len(cases),block_counts={k:len(v) for k,v in cases.items()},failed=fail,candidate=None),indent=2))
 print('FROZEN',out.read_text(),flush=True)
if __name__=='__main__':
 stages=sys.argv[1:] or ['E1','E3','E4','E5']
 for stage in stages:
  if stage!='E1':freeze()
  for b in range(6):block(stage,b)
  if stage=='E1':freeze()
