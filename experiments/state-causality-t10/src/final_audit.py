from common import *
import subprocess,collections
r=runroot();ledger=lines(r/'ledger.jsonl');begin=read(ROOT/'BEGIN_EXECUTION.json');used=sum(x['worker_s'] for x in ledger)/60
assert used<=20 and used+begin['prior_gpu_minutes']<=330
for name,h in read(ROOT/'freeze/PRIOR_HASHES.json').items():assert sha(name)==h
build=Path((ROOT/'BUILD.txt').read_text().strip());oldbuild=Path((PREVIOUS/'BUILD.txt').read_text().strip())
for n in ['diag0.cubin','diag1.cubin']:assert sha(build/n)==sha(oldbuild/n)
for n in ['backend.py','kernels.cu','kernels.cuh','resources.hpp','runtime_extra.hpp','pair_runtime.hpp','diagnostic_runtime.hpp','policy.hpp','relative_generated.hpp','decision_core.hpp']:assert sha(ROOT/'src'/n)==sha(PREVIOUS/'src'/n),n
assert (ROOT/'src/backend.cu').read_text()==(PREVIOUS/'src/backend.cu').read_text()+'\n#include "state_runtime.hpp"\n'
for n in ['bins.json','PILOTS.json']:assert sha(ROOT/'freeze'/n)==sha(PREVIOUS/'freeze'/n)
actual=[];numeric=[]
for w in ledger:
 out=r/'raw'/Path(w['out']).name
 if w['status']=='COMPLETED':actual.append(read(out/'complete.json'))
 for x in lines(out/'correctness.jsonl'):
  assert x['numerical']['status']=='PASS';numeric.append(x)
for kind,n in [('main',6),('control',2),('observer',2)]:assert len([x for x in actual if x['kind']==kind])==n
results=read(r/'derived/results.json');assert results['status']=='PASS'
state={}
for name,cmd in {'device':['nvidia-smi','-q','-d','CLOCK,POWER,PERFORMANCE'],'fan':['systemctl','status','t10-quiet-fan.service','--no-pager'],'kernel':['journalctl','-k','--since',datetime.datetime.fromisoformat(begin['started_at']).astimezone().strftime('%Y-%m-%d %H:%M:%S'),'--no-pager'],'apps':['nvidia-smi','--query-compute-apps=pid,process_name,used_memory','--format=csv']}.items():
 p=subprocess.run(cmd,capture_output=True,text=True);state[name]=dict(command=cmd,returncode=p.returncode,stdout=p.stdout,stderr=p.stderr)
assert all(x['returncode']==0 for x in state.values())
assert 'NVRM: Xid' not in state['kernel']['stdout'] and 'GPU has fallen off' not in state['kernel']['stdout']
write(ROOT/'reports/FINAL_STATE.json',state)
write(ROOT/'reports/FINAL_AUDIT.json',dict(status='PASS',at=utc(),wall_minutes=elapsed()/60,new_gpu_minutes=used,prior_gpu_minutes=begin['prior_gpu_minutes'],cumulative_gpu_minutes=used+begin['prior_gpu_minutes'],workers=[dict(key=x['key'],status=x['status'],seconds=x['worker_s']) for x in ledger],completed_by_kind=dict(collections.Counter(x['kind'] for x in actual)),numerical_records=len(numeric),counts=results['counts'],prior_files_unchanged=True,math_and_selector_unchanged=True,system_writes=[],clock_lock='UNAVAILABLE_PERMISSION_DENIED',hardware_cache_counters='UNAVAILABLE_ADMIN_ONLY',restore='No setting changed; original100W andfanprotection remain'))
print('FINAL_AUDIT_PASS',used,used+begin['prior_gpu_minutes'])
