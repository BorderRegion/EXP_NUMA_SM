from common import *
from nvml_state import NVML
import os,sys,time,signal,fcntl,subprocess,shutil

def run(key,args,timeout=300):
 out=RUN/key;out.mkdir(parents=True,exist_ok=False);cmd=[str(a).replace('{OUT}',str(out)) for a in args]
 with (REPO/'environment/gpu_worker.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX);t=time.monotonic();ledger=RUN/'ledger.jsonl';old=[json.loads(l) for l in ledger.read_text().splitlines()] if ledger.exists() else []
  timeout=min(timeout,1800-sum(x['worker_seconds'] for x in old));assert timeout>5
  for p in [REPO/'environment/GPU_HEALTH_STOP',REPO/'op-fused/registry/GPU_HEALTH_STOP',RUN/'GPU_HEALTH_STOP']:
   if p.exists():raise RuntimeError('Health stop: '+str(p))
  if shutil.disk_usage(ROOT).free<900<<20:raise RuntimeError('Disk reserve <900 MiB')
  m=dict(key=key,started=utc(),command=cmd,cap_seconds=timeout,status='RUNNING',sources={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'src').glob('*') if p.is_file()},binaries={p.name:sha(p) for p in (ROOT/'build').glob('*') if p.suffix in ['.so','.cubin']},protocol_sha256=sha(ROOT/'freeze/PROTOCOL.json'))
  write(out/'manifest.json',m);nv=NVML();p=None;rc=-1
  try:
   before=nv.snapshot();write(out/'device_before.json',before)
   if before['limit_mw']['value']!=100000 or before['temperature_c']['value']>=82:raise RuntimeError('Initial health check')
   env=os.environ.copy();env.update(OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',PYTHONDONTWRITEBYTECODE='1',PYTHONUNBUFFERED='1')
   with (out/'stdout.log').open('w') as so,(out/'stderr.log').open('w') as se,(out/'telemetry.jsonl').open('w') as tf:
    p=subprocess.Popen(cmd,stdout=so,stderr=se,env=env,start_new_session=True,pass_fds=(lock.fileno(),));m['pid']=p.pid;write(out/'manifest.json',m)
    while True:
     snap=nv.snapshot();tf.write(json.dumps(snap)+'\n');tf.flush()
     if snap['temperature_c']['value'] is None or snap['temperature_c']['value']>=82:raise RuntimeError('Temperature guard')
     if snap['limit_mw']['value']!=100000:raise RuntimeError('Power cap changed')
     if time.monotonic()-t>timeout:raise RuntimeError('Worker budget deadline')
     try:rc=p.wait(timeout=.5);break
     except subprocess.TimeoutExpired:pass
   m['status']='COMPLETED' if rc==0 else 'FAILED';m['returncode']=rc
  except BaseException as e:m['status']='FAILED';m['error']=repr(e);raise
  finally:
   if p and p.poll() is None:
    os.killpg(p.pid,signal.SIGTERM)
    try:p.wait(timeout=5)
    except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
   write(out/'device_after.json',nv.snapshot());nv.close();m['ended']=utc();m['worker_seconds']=time.monotonic()-t;write(out/'manifest.json',m)
   with ledger.open('a') as f:f.write(json.dumps(m)+'\n')
  print(key,m['status'],round(m['worker_seconds'],3),flush=True)
  if rc:raise RuntimeError(str(out))
 return out
if __name__=='__main__':run(sys.argv[1],sys.argv[2:])
