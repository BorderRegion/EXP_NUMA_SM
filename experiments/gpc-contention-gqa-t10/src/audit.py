from common import *
import collections,csv,gzip,subprocess
ph=read(RUN/'derived/ALL_PHASES.json');counts={}
for stage,expected in [('E2',792),('E3',576),('E4',168)]:
 rr=[x for x in ph if x['stage']==stage and x['role']=='PRIMARY' and (stage=='E4' or x['view']=='single')]
 counts[stage]=len(rr);assert len(rr)==expected
 assert sorted(collections.Counter(x['block'] for x in rr).values())==[expected//6]*6
assert not read(RUN/'derived/MISSING.json')
ledger=[json.loads(x) for x in (RUN/'ledger.jsonl').read_text().splitlines()]
assert sum(x['seconds'] for x in ledger)<10800
for x in ledger:assert x.get('returncode')==0 and not x.get('stop_reason'),x
num_count=0
for f in (RUN/'raw').glob('*/NUMERICAL.json'):
 for x in read(f):assert x['status']=='PASS';num_count+=1
hashes=[]
for filename in ['E2_E3_IMPLEMENTATION.json','E4_IMPLEMENTATION.json']:
 for rel,want in read(RUN/'freeze'/filename)['hashes'].items():
  got=sha(ROOT/rel)
  # E2 froze files present before E4 existed. Its prior formal script is unchanged.
  assert got==want,(filename,rel,want,got)
  hashes.append(dict(freeze=filename,path=rel,sha256=got))
raw_requests=collections.Counter();slot_coverage={}
for f in (RUN/'raw').glob('E[234]_block_*/requests.csv.gz'):
 with gzip.open(f,'rt') as z:
  rows=list(csv.DictReader(z));raw_requests[f.parent.name]=len(rows)
  assert all(float(x.get('gpu_span_us',x.get('job_gpu_us',0)))>0 for x in rows)
profiles=read(RUN/'raw/E5_profiles/PROFILES.json');assert len(profiles)==4
trace=read(RUN/'raw/E5_gqa_placement/COMPLETE.json');assert trace['status']=='PASS' and trace['trace_launches']==480
gemm=read(RUN/'raw/E5_gemm_graph/COMPLETE.json');assert gemm['status']=='PASS' and gemm['audits']==72
san=[]
for name in ['E5_memcheck','E5_synccheck']:
 p=RUN/'raw'/name;log=(p/'stdout.log').read_text()+(p/'stderr.log').read_text();zero='ERROR SUMMARY: 0 errors' in log
 san.append(dict(worker=name,status=read(p/'manifest.json')['status'],zero_error_summary=zero,scope='24 micro launches plus 8 paged-tail GQA launches, not the entire campaign'))
 assert zero and read(p/'manifest.json')['status']=='COMPLETED'
power=subprocess.check_output(['nvidia-smi','--query-gpu=uuid,driver_version,power.limit,enforced.power.limit,temperature.gpu,clocks.sm,clocks.mem','--format=csv,noheader,nounits'],text=True).strip();parts=power.split(',');assert float(parts[2])==float(parts[3])==100
write(RUN/'reports/FINAL_POWER_READBACK.json',dict(utc=utc(),query=power,system_settings_modified_by_this_run=False,clock_lock_not_applied=True))
boot=subprocess.check_output(['uptime','-s'],text=True).strip()
audit=dict(status='PASS',run=RUN.name,primary_phase_counts=counts,numerical_records_in_formal_and_qualification=num_count,raw_timing_rows=dict(raw_requests),source_hashes_verified=hashes,all_complete_markers=True,missing_primary_cells=0,gpu_worker_seconds=sum(x['seconds'] for x in ledger),gpu_worker_cap_seconds=10800,worker_count=len(ledger),wall_start_utc=read(RUN/'freeze/RUN.json')['wall_budget_started_utc'],audit_time_utc=utc(),wall_deadline_utc=read(RUN/'freeze/RUN.json')['wall_hard_deadline_utc'],same_body_GQA_trace=trace,gemm_graph=gemm,profiles=profiles,sanitizer=san,current_boot_started_local=boot,new_downloads=0,new_installs=0,new_paid_resources=0,system_configuration_changes=0,limits=['No physical memory home or remote traffic counters','Only one T10 and one date for new measurements','95% intervals exploratory, not all-history multiplicity corrected','Initialization not included in warm request/job metric','Trace and sanitizer coverage finite; not every formal request individually inspected','E4 graph body audit is a separate diagnostic, not per-formal-phase tracing'])
write(RUN/'reports/FINAL_AUDIT.json',audit);print(json.dumps({k:audit[k] for k in ['status','primary_phase_counts','numerical_records_in_formal_and_qualification','gpu_worker_seconds']},ensure_ascii=False))
