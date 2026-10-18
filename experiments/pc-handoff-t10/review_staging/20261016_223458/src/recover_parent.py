"""Adopt one already-running child after its terminal launcher received SIGTERM."""
from common import *
import fcntl,subprocess,time,signal,os,datetime
r=runroot();out=r/'raw/E2_bridge_1';m=json.loads((out/'manifest.json').read_text());pid=m['pid'];write(out/'manifest_parent_lost.json',m)
with (REPO/'environment/gpu_worker.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX);resumed=utc();monitor=subprocess.Popen([PYTHON,str(ROOT/'src/telemetry.py'),str(out/'telemetry_resume.csv')])
 try:
  start=datetime.datetime.fromisoformat(m['lock_acquired_at']).timestamp()
  while Path(f'/proc/{pid}').exists():
   stat=Path(f'/proc/{pid}/stat').read_text().split()
   if stat[2]=='Z':break
   if time.time()-start>m['remaining_budget_at_start_s']:os.killpg(pid,signal.SIGTERM);raise RuntimeError('adopted budget timeout')
   temp=int(subprocess.check_output(['nvidia-smi','-i',UUID,'--query-gpu=temperature.gpu','--format=csv,noheader,nounits'],text=True))
   if temp>=82:os.killpg(pid,signal.SIGTERM);raise RuntimeError('adopted temperature guard')
   time.sleep(2)
  complete=json.loads((out/'complete.json').read_text()) if (out/'complete.json').exists() else {}
  rows=[json.loads(x) for x in (out/'phases.jsonl').read_text().splitlines()] if (out/'phases.jsonl').exists() else []
  ok=complete.get('status')=='PASS' and len(rows)==54 and all(x['status']=='PASS' for x in rows)
  m.update(status='COMPLETED' if ok else 'FAILED',returncode=None,process_ended_at=utc(),released_at=utc(),worker_s=time.time()-start,parent_recovery=dict(reason='Tool terminal launcher returned exit143; child remained running in its own session. No GPU/device error observed.',resumed_at=resumed,exit_code_available=False,completion_evidence='Explicit script completion marker after engine close, all54 phases PASS' if ok else 'Incomplete',telemetry_gap_recorded=True,telemetry_resume_file='telemetry_resume.csv'))
  write(out/'manifest.json',m);append(r/'ledger.jsonl',m)
  if not ok:raise RuntimeError('adopted incomplete worker')
 finally:monitor.terminate();monitor.wait(timeout=5)
query=['nvidia-smi','-i',UUID,'--query-gpu=uuid,temperature.gpu,power.limit,enforced.power.limit,clocks.sm,clocks.mem,memory.free','--format=csv'];(out/'device_after.csv').write_text(subprocess.check_output(query,text=True));print('ADOPTED_WORKER_COMPLETE',flush=True)
append(ROOT/'reports/ENGINEERING_NOTES.jsonl',dict(at=utc(),issue='Terminal launcher exited143 while bridge1 child continued; terminal-owned telemetry exited too',repair='Adopted existing child under shared lock without interrupting its computation; saved resumed telemetry separately. Retained all phases, explicit completion marker and timing gap. Queue subsequently detached from terminal, and future worker child inherits lock descriptor; SIGTERM wrapper handler settles and stops child.',worker='E2_bridge_1',exit_code_unavailable=True))
subprocess.run([PYTHON,ROOT/'src/queue_pc.py'],check=True)
