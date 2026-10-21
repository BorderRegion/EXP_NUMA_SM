"""CPU-only integrity audit and complete archive; never launches a GPU workload."""
from pathlib import Path
import csv,datetime,hashlib,json,zipfile,time,re,collections
R=Path(__file__).resolve().parents[1]
def load(p):return json.loads(p.read_text())
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(8<<20),b''):h.update(b)
    return h.hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
checks={}
freeze=load(R/'MEASUREMENT_FREEZE.json');fmap=load(R/'MAP_FREEZE.json')
checks['probe_source_matches_measurement_freeze']=sha(R/'src/affinity_probe.cu')==freeze['source_sha256']
checks['measured_probe_binary_matches_freeze']=sha(R/'build/affinity_probe')==freeze['binary_sha256']
checks['selection_source_at_freeze_retained']=sha(R/'tools/select_map_at_freeze.py')==fmap['analysis_source_sha256']
commands=[json.loads(x) for x in (R/'results/raw/commands.jsonl').read_text().splitlines()]
failed=[x for x in commands if x['status']!='PASS']
checks['only_known_repaired_API_failure']=len(failed)==1 and failed[0]['label']=='e2_control_memcheck'
checks['no_new_Xid_in_runner_records']=not any(x.get('xid_events') for x in commands)
checks['no_GPU_stop_file']=not (R/'GPU_STOP.json').exists()
checks['freeze_precedes_all_confirmation']=all(x['started']>fmap['frozen_at'] for x in commands if x['label'].startswith('e1_confirm_'))
checks['measurement_freeze_precedes_development']=all(x['started']>freeze['frozen_at'] for x in commands if x['label'].startswith('e1_dev_'))
rows=[];coverage=[];totalbytes=0;strata=set()
for epoch in range(5):
    label=f'e1_dev_{epoch}' if epoch<3 else f'e1_confirm_{epoch}';p=R/'results/raw'/label
    dispatch=list(csv.DictReader((p/'dispatches.csv').open()));offset=0
    for row in dispatch:
        assert int(row['sample_offset'])==offset
        offset+=int(row['sample_count']);assert int(row['errors'])==0
        if int(row['recipe'])<2:strata.add((epoch,int(row['pool_span_bytes']),int(row['recipe']),int(row['active_lanes'])))
    assert (p/'samples.bin').stat().st_size==offset*40
    assert len(dispatch)==648 and offset==8055936
    totalbytes+=(p/'samples.bin').stat().st_size
    rows+=dispatch;coverage.append(load(R/'results/derived'/label/'coverage.json'))
checks['formal_counts_offsets_and_CPU_checks']=len(rows)==3240 and len(strata)==60 and totalbytes==40279680*40
checks['formal_migration_free']=sum(x['migrations'] for x in coverage)==0
checks['formal_kernel_under_preferred_2ms']=max(x['max_kernel_ms'] for x in coverage)<2
checks['complete_broad_SM_region_coverage']=all(x['coverage_dense_min']==1 and x['observed_sms']==84 for x in coverage)
checks['denser_holes_disclosed']=all(x['coverage_denser_min']<1 for x in coverage)
actual=[]
for epoch,span,recipe,active in sorted(strata):
    selected=[x for x in rows if (int(x['epoch']),int(x['pool_span_bytes']),int(x['recipe']),int(x['active_lanes']))==(epoch,span,recipe,active)]
    assert len(selected)==36
    actual.append(dict(epoch=epoch,pool_span_bytes=span,recipe=recipe,active_lanes=active,cache_conditions=3,sampling_conditions=2,rounds=6,dispatches=len(selected)))
with (R/'results/derived/E1_ACTUAL_STRATA.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(actual[0]));w.writeheader();w.writerows(actual)
quality=0;timings=0
for block in range(3):
    p=R/'results/raw'/f'e2_cost_{block}'
    q=list(csv.DictReader((p/'quality.csv').open()));t=list(csv.DictReader((p/'timings.csv').open()));quality+=len(q);timings+=len(t)
    assert len(q)==18 and len(t)==1152
    assert all(int(x['missed_or_duplicate'])==int(x['output_errors'])==0 for x in q)
    group=collections.defaultdict(set)
    for x in csv.DictReader((p/'placement.csv').open()):group[int(x['group'])].add(int(x['smid']))
    assert [len(group[g]) for g in range(3)]==[40,40,4]
    assert len(set.union(*group.values()))==84
checks['control_54_exact_ownership_cases_and_3456_replays']=quality==54 and timings==3456
checks['all_full_control_blocks_use_84_observed_SMs']=True
for label in ['e2_control_memcheck_fixed','e2_control_synccheck_fixed','e2_control_racecheck_fixed']:
    p=R/'results/raw'/label;text=(p/'stdout.txt').read_text()+(p/'stderr.txt').read_text()
    checks[label+'_zero_errors']=load(p/'run.json')['returncode']==0 and bool(re.search(r'(ERROR SUMMARY: 0 errors|RACECHECK SUMMARY: 0 hazards)',text))
health=load(R/'results/derived/FINAL_HEALTH.json')
checks['final_health_readable_no_new_Xid']=health['kernel']['returncode']==health['nvidia_smi']['returncode']==0 and not health['new_xid_events'] and 'None' in health['nvidia_smi']['stdout']
checks['independent_budget_under_24_hours']=load(R/'BUDGET.json')['conservative_reserved_worker_hours']<24
checks['renderer_not_measured_or_claimed']=load(R/'plan_manifest.json')['application_end_to_end_benefit'] is None
checks['gate_failed']=load(R/'results/derived/CONFIRMATION.json')['actionable'] is False
assert all(checks.values()),checks
status=dict(status='COMPLETE_BOUNDED_STOP_AND_REPORT',finished_at=datetime.datetime.now().astimezone().isoformat(),outcome='NO_ACTIONABLE_AFFINITY_IN_TESTED_SCOPE',qualifier='Weak positive 0.331% timing prediction below frozen 3% actionability gate; no learned-map deployment or rendering speedup measured.',no_further_GPU_work=True)
save(R/'STATUS.json',status)
excluded={'FILE_MANIFEST.json','FINAL_AUDIT.json'}
files=sorted(p for p in R.rglob('*') if p.is_file() and p.relative_to(R).parts[0]!='artifacts' and '__pycache__' not in p.parts and p.name not in excluded)
index=[]
for p in files:index.append(dict(path=str(p.relative_to(R)),bytes=p.stat().st_size,sha256=sha(p)))
save(R/'FILE_MANIFEST.json',dict(created=datetime.datetime.now().astimezone().isoformat(),hash_algorithm='SHA-256',scope='All project files except artifacts, self-index/final audit and Python bytecode caches; includes every raw samples.bin',entries=index,total_bytes=sum(x['bytes'] for x in index)))
save(R/'FINAL_AUDIT.json',dict(status='PASS',checked_at=datetime.datetime.now().astimezone().isoformat(),checks=checks,command_runs=len(commands),known_failed_runs=[x['label'] for x in failed],files_hashed=len(index),manifest_sha256=sha(R/'FILE_MANIFEST.json'),
 limitations=['Learned map is predictive only; no causal matched versus shuffled execution.','No renderer sessions or deployment lifetime tests.','Only two confirmation allocations and three control process blocks.','Denser SM-region coverage incomplete; consumer 32B-sector footprint below L2.','Per-run executable hash not captured at launch; final measured probe binary matches preregistered hash, and invocations identify unchanged executable path.','No physical-address, cache-hit, traffic or actual occupancy counters.','Literature full texts not independently verified.','Initial sanitizer API failure retained and repaired; final small-case checks passed.']))
archive=R/'artifacts/STATIC_AFFINITY_5080_COMPLETED_20261013.zip'
assert not archive.exists(),'Refusing to overwrite an existing delivery archive'
tozip=files+[R/'FILE_MANIFEST.json',R/'FINAL_AUDIT.json']
print(f'Audit PASS. Packaging {len(tozip)} files, including all raw samples.',flush=True)
start=time.monotonic()
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=1,allowZip64=True) as z:
    for p in tozip:z.write(p,arcname='static-affinity-5080/'+str(p.relative_to(R)))
print(f'Archive written in {time.monotonic()-start:.1f}s; validating every decompressed file.',flush=True)
expected={x['path']:x['sha256'] for x in index}
expected.update({p.name:sha(p) for p in [R/'FILE_MANIFEST.json',R/'FINAL_AUDIT.json']})
with zipfile.ZipFile(archive) as z:
    assert len(z.namelist())==len(expected)
    for name,h in expected.items():
        digest=hashlib.sha256()
        with z.open('static-affinity-5080/'+name) as f:
            for chunk in iter(lambda:f.read(8<<20),b''):digest.update(chunk)
        assert digest.hexdigest()==h,name
result=dict(status='PASS',archive=str(archive.resolve()),bytes=archive.stat().st_size,sha256=sha(archive),all_archived_files_sha256_verified=True,raw_binary_samples_included=True,files=len(expected),manifest_sha256=sha(R/'FILE_MANIFEST.json'),completed_at=datetime.datetime.now().astimezone().isoformat())
save(R/'artifacts/ARCHIVE_CHECK.json',result)
(R/'artifacts/SHA256SUMS.txt').write_text(result['sha256']+'  '+archive.name+'\n')
print(json.dumps(result),flush=True)
