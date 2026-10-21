from common import *
import sys,subprocess,time,fcntl,os,signal
name=sys.argv[1];args=sys.argv[2:];folder=RUN/'raw'/name;folder.mkdir(parents=True,exist_ok=False)
with (REPO/'environment/gpu_worker.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 ledger=RUN/'ledger.jsonl';prior=sum(x['seconds'] for x in map(json.loads,ledger.read_text().splitlines())) if ledger.exists() else 0
 budget=10800-prior
 start=time.monotonic();p=None;reason=None
 write(folder/'manifest.json',dict(status='RUNNING',start_utc=utc(),command=args,remaining_worker_seconds=budget))
 try:
  assert budget>0
  with (folder/'stdout.log').open('w') as out,(folder/'stderr.log').open('w') as err,(folder/'telemetry.jsonl').open('w') as tel:
   env=dict(os.environ,OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='2',T10_WORKER_DIR=str(folder))
   p=subprocess.Popen(args,stdout=out,stderr=err,env=env,start_new_session=True)
   while p.poll() is None:
    q=subprocess.run(['nvidia-smi','--query-gpu=uuid,power.limit,enforced.power.limit,temperature.gpu,clocks.sm,clocks.mem,utilization.gpu,memory.used','--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=10)
    tel.write(json.dumps(dict(utc=utc(),elapsed_s=time.monotonic()-start,query=q.stdout.strip(),returncode=q.returncode))+'\n');tel.flush()
    parts=[x.strip() for x in q.stdout.strip().split(',')]
    if q.returncode or len(parts)!=8:reason='TELEMETRY_FAILURE'
    elif float(parts[3])>=82:reason='TEMPERATURE_GUARD'
    elif float(parts[1])!=100 or float(parts[2])!=100:reason='POWER_LIMIT_CHANGED'
    elif time.monotonic()-start>=budget:reason='GPU_WORKER_BUDGET'
    elif datetime.now(timezone.utc)>=datetime.fromisoformat(read(RUN/'freeze/RUN.json')['wall_hard_deadline_utc']):reason='WALL_BUDGET'
    if reason:
     os.killpg(p.pid,signal.SIGTERM);p.wait(timeout=15);break
    time.sleep(1)
   code=p.wait()
 finally:
  if p is not None and p.poll() is None:os.killpg(p.pid,signal.SIGTERM);p.wait(timeout=15)
  seconds=time.monotonic()-start;rc=p.returncode if p else None
  entry=dict(worker=name,start_utc=read(folder/'manifest.json')['start_utc'],end_utc=utc(),seconds=seconds,returncode=rc,stop_reason=reason)
  with ledger.open('a') as f:f.write(json.dumps(entry)+'\n')
  write(folder/'manifest.json',dict(**entry,status='COMPLETED' if rc==0 and not reason else 'FAILED',command=args))
 print(json.dumps(entry),flush=True)
 if rc or reason:raise SystemExit(rc or 2)
