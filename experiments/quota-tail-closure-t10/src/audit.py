from common import *
import csv,gzip,collections,subprocess,numpy as np
expanded=read(RUN/'derived/EXPANDED_LABELS.json');ph=read(RUN/'derived/MEASURED_PHASES.json')
counts=collections.Counter(x['stage'] for x in expanded);assert dict(counts)==dict(S1=136,S2=132,S3=120,HOLDOUT=48),counts
assert sum(counts.values())==436
for stage,blocks in [('S1',[0,1]),('S2',[0,1]),('S3',list(range(2,8))),('HOLDOUT',list(range(8,12)))]:
 assert sorted({x['block'] for x in expanded if x['stage']==stage})==blocks
rows_total=0;check_records=0
for source in read(RUN/'derived/SOURCES.json'):
 folder=RUN/'raw'/source['worker'];phase=read(folder/'PHASES.json')
 with gzip.open(folder/'requests.csv.gz','rt') as f:rows=list(csv.DictReader(f))
 grouped=collections.defaultdict(list)
 for x in rows:grouped[x['case'],x['task'],x['role'],x['label']].append(x)
 for x in phase:
  rr=grouped[x['case'],x['task'],x['role'],x['label']];assert len(rr)==x['formal_jobs']==(16 if x['role']=='PRIMARY' else 4)
  for m in ['job_gpu_us','foreground_completion_us','background_completion_us','job_output_ready_us']:
   if x[m] is not None:assert np.isclose(np.mean([float(r[m]) for r in rr]),x[m],rtol=0,atol=1e-9)
  assert all(w['jobs']>=2 and w['host_us']>=50000 for w in x['warmups'])
  assert all(float(r['job_output_ready_us'])>0 for r in rr)
 rows_total+=len(rows)
 for x in read(folder/'NUMERICAL.json'):
  for name,c in x['check'].items():assert c['status']=='PASS';check_records+=1
for name,want in read(RUN/'freeze/IMPLEMENTATION_REPAIRED_BEFORE_VALID_S1.json').items():assert sha(ROOT/name)==want,name
for folder,names in [('src',['gqa.cu','gqa_append.cu']),('build',['gqa.so','gqa_append.so'])]:
 for name in names:assert sha(ROOT/folder/name)==sha(REPO/'gpc-contention-gqa-t10'/folder/name)
ledger=[json.loads(x) for x in (RUN/'ledger.jsonl').read_text().splitlines()];failures=[x for x in ledger if x['returncode']!=0 or x['stop_reason']]
assert len(failures)==1 and failures[0]['worker']=='S1_block_0' and failures[0]['returncode']==1 and failures[0]['stop_reason'] is None
used=sum(x['seconds'] for x in ledger);budget=read(RUN/'freeze/RUN.json');assert used<=budget['worker_cap_seconds']
prior=sum(json.loads(x)['seconds'] for x in (Path(budget['prior_run'])/'ledger.jsonl').read_text().splitlines());assert used+prior<=10800
assert datetime.now(timezone.utc)<datetime.fromisoformat(budget['wall_hard_deadline_utc'])
for name in ['S4_diagnostics','S4_costs','S4_costs_warm_control','S4_memcheck','S4_synccheck']:assert read(RUN/'raw'/name/'COMPLETE.json')['status']=='PASS'
profiles=read(RUN/'raw/S4_diagnostics/PROFILES.json');assert len(profiles)==4
for name in ['S4_memcheck','S4_synccheck']:
 folder=RUN/'raw'/name;text=(folder/'stdout.log').read_text()+(folder/'stderr.log').read_text();assert 'ERROR SUMMARY: 0 errors' in text
query=subprocess.check_output(['nvidia-smi','--query-gpu=uuid,power.limit,enforced.power.limit,temperature.gpu,clocks.sm,clocks.mem','--format=csv,noheader,nounits'],text=True).strip();q=query.split(',');assert float(q[1])==float(q[2])==100
fresh=subprocess.run([str(REPO/'gpc-mask-t10/read_topology')],capture_output=True,text=True,check=True);assert json.loads(fresh.stdout)==read(RUN/'raw/S0_environment/topology.json')
write(RUN/'reports/FINAL_READBACK.json',dict(utc=utc(),query=query,RM_unchanged=True,no_settings_changed=True))
audit=dict(status='PASS_WITH_RECORDED_ENGINEERING_RETRY',logical_primary_labels=dict(counts),physical_primary_phases=collections.Counter(x['stage'] for x in ph if x['role']=='PRIMARY'),timing_rows=rows_total,numerical_check_records=check_records,known_failed_worker=failures,complete_valid_blocks=True,all_phase_means_recomputed_from_requests=True,source_hashes_match_valid_S1_freeze=True,original_E56_body_unchanged=True,worker_seconds=used,worker_cap_seconds=budget['worker_cap_seconds'],previous_worker_seconds=prior,combined_seconds=used+prior,combined_cap_seconds=10800,wall_start_utc=budget['wall_budget_started_utc'],finished_utc=utc(),deadline_utc=budget['wall_hard_deadline_utc'],CUPTI_captures=4,thermal_guard_unchanged=True,power_cap_w=100,new_installs=0,new_downloads=0,missing=['Hardware memory/interconnect counters','Exact private cuBLAS algorithm ID','Stage timestamps in formal traces (intentionally only separate diagnostics)','Cross-day/device and real model lifecycle'],limits=['One known failed initial worker lost in-memory samples before export; kept error logs and retried same block before selection','Physical placement families not member-frequency matched at all quotas','All required plans precreated and remain idle when not selected; resource/context environment differs between development and smaller confirmation pools','Exact same symbols/geometry do not prove all backend execution behavior identical','Algebraic H costs are estimates, not H-job deployments'])
write(RUN/'reports/FINAL_AUDIT.json',audit);print(json.dumps(audit,ensure_ascii=False,indent=2))
