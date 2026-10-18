"""New 24 h ledger; same machine-wide GPU lock. No old ledger mutations."""
import argparse, fcntl, json, os, shutil, signal, subprocess, time
from common import *
CAPS={'P0':7200,'P1':21600,'P2':10800,'P3':18000,'P4':18000,'P5':7200,'P6':3600}
def run(stage,key,command):
 r=runroot();ledger=r/'ledger.jsonl';rows=[json.loads(x) for x in ledger.read_text().splitlines()] if ledger.exists() else []
 if any(x['key']==key for x in rows): raise RuntimeError('Key already recorded; use a documented retry key')
 out=r/'raw'/key;out.mkdir(parents=True,exist_ok=False)
 m=dict(key=key,stage=stage,status='REQUESTED',requested_at=utc(),command=[str(x) for x in command],out=str(out),device_uuid=UUID)
 def save():write(out/'manifest.json',m)
 save()
 with open(REPO/'environment/gpu_worker.lock','a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX);m['lock_acquired_at']=utc();start=time.monotonic()
  rows=[json.loads(x) for x in ledger.read_text().splitlines()] if ledger.exists() else []
  remain=min(86400-sum(x['worker_s'] for x in rows),CAPS[stage]-sum(x['worker_s'] for x in rows if x['stage']==stage))
  if remain<=0:raise RuntimeError('GPU-worker budget exhausted')
  for p in [REPO/'environment/GPU_HEALTH_STOP',REPO/'op-fused/registry/GPU_HEALTH_STOP',r/'GPU_HEALTH_STOP']:
   if p.exists():raise RuntimeError('Health stop: '+str(p))
  if shutil.disk_usage(r).free<3*2**30:raise RuntimeError('Disk reserve')
  cmd=[str(x).replace('{OUT}',str(out)) for x in command];m['command']=cmd
  sources={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'src').glob('*') if p.is_file()}
  m['source_hashes']=sources;m['protocol_sha256']=sha(r/'manifest.json')
  m['git_commit']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()
  m['binary_hashes']={str(p.relative_to(r)):sha(p) for p in (r/'compiled').rglob('*') if p.is_file() and (p.suffix in ['.cubin','.so'] or p.name in ['probe_runner','render_native','fine_runner','micro_campaign','micro_lifecycle','green_graph_qualification'])}
  patch=subprocess.check_output(['git','diff','--no-ext-diff','HEAD'],cwd=REPO)
  (out/'tracked_dirty.patch').write_bytes(patch);m['dirty_patch_sha256']=sha(out/'tracked_dirty.patch')
  m['untracked_source_provenance']='source_hashes plus compiled source snapshots; new project is initially untracked'
  write(out/'sources.json',sources)
  query=['nvidia-smi','-i',UUID,'--query-gpu=uuid,temperature.gpu,memory.free,power.limit,enforced.power.limit,clocks.sm,clocks.mem','--format=csv']
  (out/'device_before.csv').write_text(subprocess.check_output(query,text=True))
  env=os.environ.copy();env.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_DATASETS_OFFLINE='1',OMP_NUM_THREADS='2',MKL_NUM_THREADS='2',MAX_JOBS='2',NUMA_V3_RUN=str(r),PYTHONDONTWRITEBYTECODE='1')
  mon=subprocess.Popen([PYTHON,str(ROOT/'src/telemetry.py'),str(out/'telemetry.csv')],env=env)
  p=None
  try:
   with open(out/'stdout.log','w') as so,open(out/'stderr.log','w') as se:
    m.update(status='RUNNING',process_started_at=utc());p=subprocess.Popen(cmd,stdout=so,stderr=se,env=env,start_new_session=True);m['pid']=p.pid;save()
    try:rc=p.wait(timeout=max(1,remain-(time.monotonic()-start)))
    except subprocess.TimeoutExpired:
     m['budget_timeout']=True;os.killpg(p.pid,signal.SIGTERM)
     try:rc=p.wait(timeout=5)
     except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);rc=p.wait()
    m.update(returncode=rc,status='COMPLETED' if rc==0 else 'FAILED',process_ended_at=utc())
  finally:
   if p and p.poll() is None:os.killpg(p.pid,signal.SIGTERM);p.wait(timeout=10)
   mon.terminate();mon.wait(timeout=5)
   m.update(worker_s=time.monotonic()-start,released_at=utc());save()
   with ledger.open('a') as f:f.write(json.dumps(m,ensure_ascii=False)+'\n')
  errors=(out/'stderr.log').read_text()
  if any(t in errors for t in ['CUDA_ERROR_ILLEGAL_ADDRESS','CUDA_ERROR_ECC_UNCORRECTABLE','CUDA_ERROR_GPU_IS_LOST','device-side assert','CUDA_ERROR_LAUNCH_FAILED']):
   (r/'GPU_HEALTH_STOP').write_text(key+'\n'+errors)
  (out/'device_after.csv').write_text(subprocess.check_output(query,text=True))
 print(key,m['status'],round(m['worker_s'],2),flush=True)
 if m['status']!='COMPLETED':raise RuntimeError(str(out))
 return out
if __name__=='__main__':
 import sys
 run(sys.argv[1],sys.argv[2],sys.argv[3:])
