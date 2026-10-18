"""Read-only raw/provenance audit. Writes a separate report, never patches raw."""
import ast,collections,datetime,hashlib,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
def sha(data):return hashlib.sha256(data).hexdigest()
def asthash(source,name):
 for n in ast.parse(source).body:
  if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==name:
   return sha(ast.dump(n,include_attributes=False).encode())
 return None
def main():
 reg=[json.loads(x) for x in (ROOT/'registry/runs.jsonl').read_text().splitlines()]
 records=[];mismatches=[];functions=collections.defaultdict(set);strong_functions=collections.defaultdict(set);failures=[];checks=0;warmbad=[];powers=collections.Counter()
 for m in reg:
  root=ROOT/m['path'];snap=root/'source_snapshot.py';b=snap.read_bytes();actual=sha(b)
  record=dict(key=m['key'],raw_manifest_hash=m['source_sha256'],actual_snapshot_sha256=actual,match=m['source_sha256']==actual,source_snapshot=str(snap.relative_to(ROOT)))
  if not record['match']:mismatches.append(record)
  records.append(record)
  assert json.loads((root/'manifest.json').read_text())==m
  if m['status']=='COMPLETED':assert (root/'COMPLETE').exists()
  if '_native_block_' in m['key']:
   for name in ['grouped','layer','attention','phase','capture']:
    if name=='grouped' and m['stage'] not in ['E1','E3']:continue
    if name=='layer' and m['stage']!='E4':continue
    if name=='attention' and m['stage']!='E5':continue
    functions[name].add(asthash(b.decode(),name))
  if '_strong_block_' in m['key']:
   for name in ['case_run','make_layer']:strong_functions[name].add(asthash(b.decode(),name))
   dependency=root/'dependency_grouped_library.py'
   cls=next(n for n in ast.parse(dependency.read_text()).body if isinstance(n,ast.ClassDef) and n.name=='Grouped')
   for n in cls.body:
    if isinstance(n,ast.FunctionDef) and n.name in ['__init__','__call__']:strong_functions['Grouped.'+n.name].add(sha(ast.dump(n,include_attributes=False).encode()))
   strong_functions['shared_native_math_file'].add(sha((root/'dependency_native_bench.py').read_bytes()))
  for p in root.glob('*.json'):
   x=json.loads(p.read_text())
   if 'case' not in x:continue
   if x.get('status') in ['FAILED','MEMORY_UNSUPPORTED','BUDGET_SKIPPED']:failures.append(dict(key=m['key'],raw_ref=str(p.relative_to(ROOT)),status=x['status'],reason=x.get('error')))
   for y in x.get('phases',[]):
    if y.get('warmup_repeats',0)<64 or y.get('warmup_device_ms',0)<300:warmbad.append([m['key'],x['case']['case_id'],y['variant']])
    for c in y.get('correctness',[]):
     checks+=1;assert c['pass'],(p,c)
 intervals=sorted(reg,key=lambda x:x['lock_acquired_at']);overlaps=[]
 for a,b in zip(intervals,intervals[1:]):
  if a['released_at']>b['lock_acquired_at']:overlaps.append([a['key'],b['key']])
 pending=[]
 outcomes=ROOT/'registry/request_outcomes.jsonl'
 resolved={x['run_id']:x for x in map(json.loads,outcomes.read_text().splitlines())} if outcomes.exists() else {}
 for p in (ROOT/'runs').glob('*/manifest.json'):
  x=json.loads(p.read_text())
  if x['status'] not in ['COMPLETED','FAILED'] and x['run_id'] not in resolved:pending.append(dict(key=x['key'],status=x['status'],path=str(p.relative_to(ROOT))))
 report=dict(completed_registry_rows=len(reg),source_records=records,source_hash_mismatches=mismatches,explanation='Earlier worker versions hashed source when requested, then snapshotted at lock acquisition. Queued edits created mismatches. Immutable lock-time source snapshots are authoritative; raw records retained unmodified. Later worker saves both requested and lock-time hash. Function stability checks only stages actually using each function: grouped E1/E3, layer E4, attention E5; phase/capture all native stages. Earlier unused layer definition differed only in a later-added route-identity ledger hash.',native_function_ast_hashes={k:sorted(v) for k,v in functions.items()},active_native_functions_stable=all(len(v)==1 for v in functions.values()),all_saved_numeric_checks=checks,all_saved_numeric_checks_pass=True,warmup_violations=warmbad,raw_failures=failures,worker_lock_overlap=overlaps,pending_manifests=pending)
 (ROOT/'reports/SOURCE_PROVENANCE_AUDIT.json').write_text(json.dumps(report,indent=2))
 report['strong_math_function_hashes']={k:sorted(v) for k,v in strong_functions.items()}
 report['strong_math_stable_despite_graph_audit_repair']=all(len(v)==1 for v in strong_functions.values())
 (ROOT/'reports/SOURCE_PROVENANCE_AUDIT.json').write_text(json.dumps(report,indent=2))
 print(json.dumps({k:report[k] for k in ['completed_registry_rows','active_native_functions_stable','all_saved_numeric_checks','warmup_violations','raw_failures','worker_lock_overlap','pending_manifests']},indent=2))
if __name__=='__main__':main()
