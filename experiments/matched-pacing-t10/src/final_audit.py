from common import *
import subprocess,zipfile,collections,ast
r=runroot();begin=read(ROOT/'BEGIN_EXECUTION.json');ledger=lines(r/'ledger.jsonl');d=read(r/'derived/results.json');used=sum(x['worker_s'] for x in ledger)/60
assert used<=begin['new_gpu_cap_minutes'] and used+begin['prior_gpu_minutes']<=330
for p,h in read(ROOT/'freeze/PRIOR_HASHES.json').items():assert sha(p)==h
for p,h in read(ROOT/'freeze/EXECUTION_SOURCES.json').items():assert sha(ROOT/p)==h,p
build=Path((ROOT/'BUILD.txt').read_text().strip());oldbuild=Path((PREVIOUS/'BUILD.txt').read_text().strip())
for n,h in read(ROOT/'freeze/BINARY_HASHES.json').items():assert sha(build/n)==h==sha(oldbuild/n)
for n in ['backend.py','backend.cu','kernels.cu','kernels.cuh','resources.hpp','runtime_extra.hpp','pair_runtime.hpp','diagnostic_runtime.hpp','state_runtime.hpp','policy.hpp','relative_generated.hpp','decision_core.hpp','diag.py','nvml_state.py','telemetry.py']:assert sha(ROOT/'src'/n)==sha(PREVIOUS/'src'/n),n
numeric=[];snapshots=0
for w in ledger:
 out=r/'raw'/Path(w['out']).name
 with zipfile.ZipFile(out/'source_snapshot.zip') as z:
  for n,h in w['sources'].items():assert hashlib.sha256(z.read('src/'+n)).hexdigest()==h;snapshots+=1
 for x in lines(out/'correctness.jsonl'):assert x['numerical']['status']=='PASS';numeric.append(x)
 assert read(out/'manifest.json')['status']==w['status']
assert d['status']=='PASS'
state={}
for name,cmd in {'device':['nvidia-smi','-q','-d','CLOCK,POWER,PERFORMANCE'],'fan':['systemctl','is-active','t10-quiet-fan.service'],'apps':['nvidia-smi','--query-compute-apps=pid,process_name,used_memory','--format=csv'],'kernel':['journalctl','-k','--since',datetime.datetime.fromisoformat(begin['started_at']).astimezone().strftime('%Y-%m-%d %H:%M:%S'),'--no-pager']}.items():
 p=subprocess.run(cmd,capture_output=True,text=True);assert p.returncode==0;(ROOT/'reports'/('final_'+name+'.txt')).write_text(p.stdout+p.stderr);state[name]=dict(returncode=p.returncode,stdout=p.stdout,stderr=p.stderr)
assert 'NVRM: Xid' not in state['kernel']['stdout'] and 'GPU has fallen off' not in state['kernel']['stdout']
for p in [*ROOT.glob('src/*.py'),ROOT/'recompute.py']:
 if p.exists():ast.parse(p.read_text(),filename=str(p))
write(ROOT/'reports/FINAL_AUDIT.json',dict(status='PASS',at=utc(),formal_complete=d['formal_complete'],completed_formal_blocks=len(d['blocks']),new_gpu_minutes=used,prior_gpu_minutes=begin['prior_gpu_minutes'],cumulative_gpu_minutes=used+begin['prior_gpu_minutes'],new_cap_minutes=begin['new_gpu_cap_minutes'],cumulative_cap_minutes=330,workers=[dict(key=x['key'],status=x['status'],worker_s=x['worker_s']) for x in ledger],numerical_records=len(numeric),source_snapshot_hash_checks=snapshots,all_previous_files_unchanged=True,all_execution_sources_frozen=True,identical_previous_binaries=True,identical_input_fixture=d['same_fixture_all_workers'],fixed_idle_cpu_only_s=sum(x['preparation']['actual_s'] for x in d['workers'] if x['kind']=='matched'),wall_minutes=elapsed()/60,clock_lock='NOT_RUN_NO_ADMIN',hardware_cache_counters='NOT_RUN_ADMIN_ONLY',system_settings_changed=False,scope='Fixed idle preparation has no GPU context or reservation; counted separately in walltime. No fullcold/hotfactorial or adaptivepolicy validation.'))
print('FINAL_AUDIT_PASS',used,used+begin['prior_gpu_minutes'])
