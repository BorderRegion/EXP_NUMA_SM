"""Finite follow-up workers, one existing GPU lock, independent 24-hour campaign debit."""
import csv,fcntl,json,os,signal,subprocess,time,shutil
from common import *
def run(key,command):
 def terminated(signum,frame):raise SystemExit('Worker launcher received SIGTERM')
 signal.signal(signal.SIGTERM,terminated)
 r=runroot();ledger=r/'ledger.jsonl';rows=[json.loads(s) for s in ledger.read_text().splitlines()] if ledger.exists() else []
 if any(x['key']==key for x in rows):raise RuntimeError('Preserve settled worker; use documented retry key')
 out=r/'raw'/key;out.mkdir(parents=True,exist_ok=False);m=dict(key=key,requested_at=utc(),status='REQUESTED',out=str(out),command=list(map(str,command)))
 write(out/'manifest.json',m)
 with (REPO/'environment/gpu_worker.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX);start=time.monotonic();m['lock_acquired_at']=utc()
  rows=[json.loads(s) for s in ledger.read_text().splitlines()] if ledger.exists() else []
  cap=24*3600
  stage=key.split('_')[0] if key.startswith(('E1_','E2_','E3_','E4_','E5_','E6_')) else 'E0'
  stage_caps={'E0':1,'E1':4,'E2':4,'E3':6,'E4':4,'E5':3,'E6':1}
  spent_stage=sum(x['worker_s'] for x in rows if x.get('stage',x['key'].split('_')[0] if x['key'].startswith(('E1_','E2_','E3_','E4_','E5_','E6_')) else 'E0')==stage)
  remain=min(cap-sum(x['worker_s'] for x in rows),stage_caps[stage]*3600-spent_stage);m['stage']=stage;m['remaining_budget_at_start_s']=remain
  assert remain>0 and shutil.disk_usage(r).free>512*2**20
  for p in [REPO/'environment/GPU_HEALTH_STOP',REPO/'op-fused/registry/GPU_HEALTH_STOP',r/'GPU_HEALTH_STOP']:
   if p.exists():raise RuntimeError('GPU health stop '+str(p))
  m['sources']={p.name:sha(p) for p in (ROOT/'src').glob('*') if p.is_file()};build=Path((ROOT/'BUILD.txt').read_text().strip());m['binaries']={p.name:sha(p) for p in build.iterdir() if p.suffix in ['.so','.cubin']};m['git_commit']=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
  query=['nvidia-smi','-i',UUID,'--query-gpu=uuid,temperature.gpu,power.limit,enforced.power.limit,clocks.sm,clocks.mem,memory.free','--format=csv'];(out/'device_before.csv').write_text(subprocess.check_output(query,text=True));apps=['nvidia-smi','-i',UUID,'--query-compute-apps=pid,process_name,used_memory','--format=csv'];(out/'compute_apps_before.csv').write_text(subprocess.check_output(apps,text=True))
  cmd=[str(x).replace('{OUT}',str(out)) for x in command];m['command']=cmd;env=os.environ.copy();env.update(PC_RUN=str(r),HF_HUB_OFFLINE='1',OMP_NUM_THREADS='2',MKL_NUM_THREADS='2',PYTHONDONTWRITEBYTECODE='1')
  mon=subprocess.Popen([PYTHON,str(ROOT/'src/telemetry.py'),str(out/'telemetry.csv')],env=env)
  p=None
  try:
   with (out/'stdout.log').open('w') as so,(out/'stderr.log').open('w') as se:
    p=subprocess.Popen(cmd,stdout=so,stderr=se,env=env,start_new_session=True,pass_fds=(lock.fileno(),));m.update(pid=p.pid,process_started_at=utc(),status='RUNNING');write(out/'manifest.json',m)
    try:
     while True:
      try:rc=p.wait(timeout=max(.1,min(5,remain-(time.monotonic()-start))));break
      except subprocess.TimeoutExpired:
       if time.monotonic()-start>=remain:raise
       telemetry=out/'telemetry.csv'
       if telemetry.exists():
        rows_now=list(csv.DictReader(telemetry.open()))
        if rows_now and rows_now[-1].get('temperature_c','').isdigit() and int(rows_now[-1]['temperature_c'])>=82:
         (r/'GPU_HEALTH_STOP').write_text('Temperature guard reached82C; stop without forcing power above protection')
         m['health_guard_stop']=True;os.killpg(p.pid,signal.SIGTERM);rc=p.wait(timeout=5);break
    except subprocess.TimeoutExpired:
     m['budget_timeout']=True;os.killpg(p.pid,signal.SIGTERM)
     try:rc=p.wait(timeout=5)
     except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);rc=p.wait()
    m.update(status='COMPLETED' if rc==0 else 'FAILED',returncode=rc,process_ended_at=utc())
  except BaseException as ex:
   m.update(status='FAILED',exception=repr(ex),process_started=p is not None);raise
  finally:
   if p and p.poll() is None:os.killpg(p.pid,signal.SIGTERM);p.wait(timeout=10)
   mon.terminate();mon.wait(timeout=5);m.update(released_at=utc(),worker_s=time.monotonic()-start);write(out/'manifest.json',m)
   with ledger.open('a') as f:f.write(json.dumps(m,ensure_ascii=False)+'\n')
  (out/'device_after.csv').write_text(subprocess.check_output(query,text=True));(out/'compute_apps_after.csv').write_text(subprocess.check_output(apps,text=True))
  errors=(out/'stderr.log').read_text()
  if any(x in errors for x in ['CUDA_ERROR_ILLEGAL_ADDRESS','CUDA_ERROR_ECC_UNCORRECTABLE','CUDA_ERROR_GPU_IS_LOST','device-side assert','CUDA_ERROR_LAUNCH_FAILED']):(r/'GPU_HEALTH_STOP').write_text(errors)
 print(key,m['status'],round(m['worker_s'],2),flush=True)
 if m['status']!='COMPLETED':raise RuntimeError(str(out))
 return out
if __name__=='__main__':
 import sys
 run(sys.argv[1],sys.argv[2:])
