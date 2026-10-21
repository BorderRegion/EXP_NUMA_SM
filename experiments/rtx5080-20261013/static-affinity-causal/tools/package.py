from pathlib import Path
import csv,datetime,hashlib,json,re,zipfile
R=Path(__file__).resolve().parents[1]
def load(p):return json.loads(p.read_text())
def save(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8<<20),b''):h.update(b)
 return h.hexdigest()
c=load(R/'CAUSAL_COMPLETION_CONTRACT.json');freeze=load(R/'BINARY_FREEZE.json');checks={}
checks['contract_unchanged']=sha(R/'CAUSAL_COMPLETION_CONTRACT.json')==freeze['contract_sha256']
checks['source_and_executable_unchanged']=sha(R/'src/causal.cu')==freeze['source_sha256'] and sha(R/'build/causal')==freeze['binary_sha256']
runs=[json.loads(x) for x in (R/'results/raw/commands.jsonl').read_text().splitlines()];formal=[x for x in runs if x['label'].startswith('f3_')]
checks['all_24_formal_processes_complete']=len(formal)==24 and all(x['status']=='PASS' for x in formal)
checks['all_final_binary_and_freeze_before_run']=all(x['source_sha256']==freeze['source_sha256'] and x['binary_sha256']==freeze['binary_sha256'] and x['started']>freeze['frozen_at'] for x in formal)
expected=[f"f3_{x['scope'].lower()}_r{x['recipe']}_b{x['block']}" for x in c['process_plan']]
checks['process_sequence_matches_frozen_plan']=[x['label'] for x in formal]==expected
total=0;latins={};max_cpu=0
for plan,label in zip(c['process_plan'],expected):
 p=R/'results/raw'/label;m=load(p/'metadata.json');rows=list(csv.DictReader((p/'timings.csv').open()));q=list(csv.DictReader((p/'quality.csv').open()));total+=len(rows)
 assert m['seed']==plan['seed'] and m['block']==plan['block'] and m['recipe']==plan['recipe']
 assert len(rows)==768 and len(q)==12 and m['group_unknown']==m['group_mismatch']==m['output_errors']==0
 assert m['observed_group_SM_counts']==[40,40,4]
 assert all(int(row[k])==0 for row in q for k in ['output_errors','ownership_errors','group_unknown','group_mismatch'])
 order=list(dict.fromkeys(int(x['policy']) for x in rows));assert order==plan['order'];latins[plan['scope'],plan['recipe'],plan['block']]=order
 for policy in range(6):
  assert [int(x['repeat']) for x in rows if int(x['policy'])==policy]==list(range(128))
  assert (p/f'output_policy{policy}.bin').read_bytes()==(p/'expected_uint2.bin').read_bytes()
 for row in rows:
  assert all(int(row[k])==0 for k in ['planner_calls','schedule_H2D_bytes','schedule_D2H_bytes'])
  max_cpu=max(max_cpu,float(row['cpu_ready_ms']))
for scope in ['SMALL','PRESSURE']:
 for rec in [0,1]:
  for pos in range(6):assert set(latins[scope,rec,b][pos] for b in range(6))==set(range(6))
checks['144_sessions_18432_epochs_exact_outputs']=total==18432
checks['Latin_positions_and_policy_order_verified']=True
checks['placement_ownership_and_remainder_verified']=load(R/'EXECUTED_ASSIGNMENT_AUDIT.json')['status']=='PASS'
checks['no_formal_diagnostics']=all(not x[k] for x in load(R/'results/derived/FORMAL_DIAGNOSTIC_ABSENCE.json') if not x['diagnostic'] for k in ['SM_register','clock_register','atomic_instruction'])
for label in ['f1_fixed_memcheck_0','f1_fixed_memcheck_1','f1_fixed_synccheck_1','f1_fixed_racecheck_0']:
 p=R/'results/raw'/label;text=(p/'stdout.txt').read_text()+(p/'stderr.txt').read_text();checks[label]=load(p/'run.json')['returncode']==0 and bool(re.search(r'(ERROR SUMMARY: 0 errors|RACECHECK SUMMARY: 0 hazards)',text))
health=load(R/'results/derived/FINAL_HEALTH.json');checks['no_new_GPU_fault']=not any(x['new_xid'] for x in runs) and not (R/'GPU_STOP.json').exists() and health['kernel']['returncode']==0 and not health['new_Xid'] and 'None' in health['device']['stdout']
budget=load(R/'BUDGET.json');checks['worker_budget_within_4h']=budget['reserved_worker_hours']<4
now=datetime.datetime.now().astimezone();budget['cpu_phase_wall_before_GPU_seconds']=(datetime.datetime.fromisoformat(budget['started'])-datetime.datetime.fromisoformat(c['created'])).total_seconds();budget['cpu_phase_wall_after_GPU_through_audit_seconds']=(now-datetime.datetime.fromisoformat(budget['released'])).total_seconds();budget['cpu_phase_note']='Elapsed wall windows, not measured CPU utilization or extra GPU reservation. Engineering between first and last GPU command remains included in worker wall time.';save(R/'BUDGET.json',budget)
old=R.parent/'static-affinity-5080';old_manifest=load(old/'FILE_MANIFEST.json');oldchecked=0
for x in old_manifest['entries']:
 assert sha(old/x['path'])==x['sha256'],f"Prior file changed: {x['path']}";oldchecked+=1
checks['prior_campaign_manifest_files_unchanged']=True
inputaudit=load(R/'results/derived/INPUT_HOLDOUT_AUDIT.json');checks['input_overlap_disclosed']=len(inputaudit['overlaps'])==4 and inputaudit['formal_seeds_mutually_distinct']
report=(R/'STATIC_AFFINITY_CAUSAL_COMPLETION.md').read_text()
for target in re.findall(r'\]\(([^)]+)\)',report):assert (R/target).exists(),target
checks['all_report_links_exist']=True
assert all(checks.values()),checks
failures=[dict(label=x['label'],status=x['status'],raw_directory='results/raw/'+x['label']) for x in runs if x['status']!='PASS']
failures.append(dict(label='initial_binary_freeze_check',status='CPU_ASSERTION_REFUSED_FREEZE',raw_directory=None,reason='One of four full-size qualifications failed; only three metadata files existed. No BINARY_FREEZE was written until corrected qualification passed.'))
save(R/'results/derived/FAILURE_LEDGER.json',failures)
save(R/'STATUS.json',dict(status='COMPLETE_WITH_DISCLOSED_PROTOCOL_DEVIATION',completed_at=now.isoformat(),outcome=load(R/'results/derived/SUMMARY.json')['overall_status'],further_GPU_work=False,input_holdout_deviation='Four PRESSURE seeds overlap qualification; see INPUT_HOLDOUT_AUDIT.json',all_144_formal_sessions_completed=True))
files=sorted(p for p in R.rglob('*') if p.is_file() and p.relative_to(R).parts[0]!='artifacts' and '__pycache__' not in p.parts and p.name not in ['FILE_MANIFEST.json','FINAL_AUDIT.json'])
entries=[dict(path=str(p.relative_to(R)),bytes=p.stat().st_size,sha256=sha(p)) for p in files]
save(R/'FILE_MANIFEST.json',dict(created_at=now.isoformat(),entries=entries,total_bytes=sum(x['bytes'] for x in entries),excluded='Artifact directory, Python caches and self-indexing manifest/audit only. All decisive raw data included.'))
save(R/'FINAL_AUDIT.json',dict(status='PASS_WITH_DISCLOSED_PROTOCOL_DEVIATION',checks=checks,prior_campaign_manifest_files_verified=oldchecked,formal_sessions=144,measured_epochs=total,max_CPU_epoch_ms=max_cpu,manifest_sha256=sha(R/'FILE_MANIFEST.json'),protocol_deviation=inputaudit,limitations=['CACHE_PRESSURE_SUPPORTED not unambiguously established; no DRAM counters.','Formal placement inferred from unchanged context/table binding and before/after diagnostics, not per-task formal tracing.','Six block exploratory intervals without multiplicity correction.','Deployment-only initialization and renderer benefit not measured.']))
archive=R/'artifacts/STATIC_AFFINITY_CAUSAL_COMPLETION_20261013.zip';assert not archive.exists()
files += [R/'FILE_MANIFEST.json',R/'FINAL_AUDIT.json'];expected={str(p.relative_to(R)):sha(p) for p in files}
print(f'Integrity checks passed; prior {oldchecked} files unchanged. Packaging {len(files)} files.',flush=True)
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in files:z.write(p,'static-affinity-causal-5080/'+str(p.relative_to(R)))
with zipfile.ZipFile(archive) as z:
 assert len(z.namelist())==len(expected)
 for name,h in expected.items():assert hashlib.sha256(z.read('static-affinity-causal-5080/'+name)).hexdigest()==h,name
result=dict(status='PASS',archive=str(archive.resolve()),bytes=archive.stat().st_size,sha256=sha(archive),all_entries_SHA256_verified=True,files=len(files),decisive_raw_data_included=True,completed_at=datetime.datetime.now().astimezone().isoformat())
save(R/'artifacts/ARCHIVE_CHECK.json',result);(R/'artifacts/SHA256SUMS.txt').write_text(result['sha256']+'  '+archive.name+'\n');print(json.dumps(result),flush=True)
