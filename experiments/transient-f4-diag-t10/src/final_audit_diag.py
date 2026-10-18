from common import *
import csv,collections,gzip,math,subprocess
r=runroot();d=read(r/'derived/diagnostic_results.json');ledger=lines(r/'ledger.jsonl');begin=read(ROOT/'BEGIN_EXECUTION.json');stages=collections.defaultdict(float)
for x in ledger:stages[x['key'].split('_')[0]]+=x['worker_s']/60
caps={'D1':5,'D2':40,'D3':25,'D4':10,'D5':5}
assert all(v<=caps[s]+1e-6 for s,v in stages.items()),stages
assert sum(stages.values())<=min(85,330-begin['prior_gpu_minutes'])+1e-6
oldhashes=read(ROOT/'freeze/INHERITED_HASHES.json');prior_audit={}
for name,h in oldhashes.items():
 p=REPO/name
 assert p.exists() and sha(p)==h,name
prior_audit['unchanged_prior_files']=len(oldhashes)
build=Path((ROOT/'BUILD.txt').read_text().strip());oldbuild=Path((PRIOR/'BUILD.txt').read_text().strip())
for n in ['diag0.cubin','diag1.cubin']:assert sha(build/n)==sha(oldbuild/n)
for n in ['kernels.cu','kernels.cuh','policy.hpp','relative_generated.hpp','decision_core.hpp','resources.hpp','runtime_extra.hpp','pair_runtime.hpp']:assert sha(ROOT/'src'/n)==sha(PRIOR/'src'/n),n
assert (ROOT/'src/backend.cu').read_text()==(PRIOR/'src/backend.cu').read_text()+'\n#include "diagnostic_runtime.hpp"\n'
checks=[];raw_counts=collections.Counter();attempts=[]
for m in ledger:
 out=r/'raw'/Path(m['out']).name
 attempts.append(dict(key=m['key'],status=m['status'],worker_s=m['worker_s']))
 for x in lines(out/'correctness.jsonl'):
  if 'numerical' in x:
   assert x['numerical']['status']=='PASS';checks.append(x)
 for p in out.glob('*.requests.csv.gz'):
  with gzip.open(p,'rt') as f:raw_counts['all_request_rows_including_pilot_and_engineering_attempts']+=sum(1 for _ in csv.DictReader(f))
 for p in out.glob('*.profile_requests.csv.gz'):
  with gzip.open(p,'rt') as f:raw_counts['profile_request_rows']+=sum(1 for _ in csv.DictReader(f))
 for p in out.glob('*.conditioning_edges.csv.gz'):
  with gzip.open(p,'rt') as f:raw_counts['conditioning_edge_rows']+=sum(1 for _ in csv.DictReader(f))
 for p in out.glob('*.conditioning.json'):
  x=read(p);raw_counts['conditioned_requests_from_counts']+=x['replays'];raw_counts['conditioned_finite64_packets']+=len(x['chunks'])
for m in ledger:
 out=r/'raw'/Path(m['out']).name
 if (out/'legacy_conditioning.json').exists():
  x=read(out/'legacy_conditioning.json');raw_counts['conditioned_requests_from_counts']+=x['replays'];raw_counts['conditioned_finite64_packets']+=len(x['chunks'])
 for p in out.glob('*.capture_conditioning.json'):
  x=read(p);raw_counts['conditioned_requests_from_counts']+=x['info'][2];raw_counts['conditioned_finite64_packets']+=x['info'][3]
captures=read(r/'derived/profile_activity.json');assert len(captures['captures'])<=6
readback={}
for name,cmd in {'device':['nvidia-smi','--query-gpu=uuid,power.limit,enforced.power.limit,temperature.gpu,clocks.sm,clocks.mem','--format=csv'],'fan':['systemctl','status','t10-quiet-fan.service','--no-pager'],'kernel':['journalctl','-k','--since',datetime.datetime.fromisoformat(begin['started_at']).astimezone().strftime('%Y-%m-%d %H:%M:%S'),'--no-pager']}.items():
 p=subprocess.run(cmd,capture_output=True,text=True);readback[name]=dict(command=cmd,returncode=p.returncode,stdout=p.stdout,stderr=p.stderr)
assert all(x['returncode']==0 for x in readback.values()),readback
assert 'NVRM: Xid' not in readback['kernel']['stdout'] and 'GPU has fallen off' not in readback['kernel']['stdout']
write(ROOT/'reports/FINAL_STATE_AND_RESTORE.json',dict(at=utc(),readback=readback,system_changes_performed=[],restore='NO_SYSTEM_WRITES; fixed100W and original fan/protection kept. No pending setting change.'))
result=dict(status='PASS',at=utc(),wall_minutes=elapsed()/60,stage_gpu_minutes=dict(stages),new_gpu_minutes=sum(stages.values()),prior_gpu_minutes=begin['prior_gpu_minutes'],cumulative_gpu_minutes=begin['prior_gpu_minutes']+sum(stages.values()),planned_work_units=d['episodes_by_kind'],planned_timing_rows=d['counts'],all_raw_counts=dict(raw_counts),numeric_checks=len(checks),captures=len(captures['captures']),immutable_math_and_selector='PASS',prior_untouched=prior_audit,attempts=attempts,clock_lock='NA_NO_NONINTERACTIVE_ADMIN',api_patch='NONE_NO_CONFIRMED_EVENT_API_BUG',scope_limitations=['FULL excludes fresh roster probe','D4 F4 no additional30s conditioner, predeclared','Optional5Hz status in OPTIONAL_OBSERVER.json','Old per-request warmup timing missing'])
write(ROOT/'reports/FINAL_AUDIT.json',result);print(json.dumps(result,indent=2))
