from pathlib import Path
import datetime,json,os,subprocess,sys,time,hashlib
ROOT=Path(__file__).resolve().parents[1]
OLD=ROOT.parent/'affinity-render-5080'
ENV=os.environ.copy();ENV['LD_LIBRARY_PATH']=str(OLD/'offline_inbox/toolchain/cuda-13.2/lib')+':'+ENV.get('LD_LIBRARY_PATH','')
def now():return datetime.datetime.now().astimezone().isoformat()
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def execute(label,argv):
    if (ROOT/'GPU_STOP.json').exists():raise RuntimeError('GPU stop active')
    budget=ROOT/'worker_start.json'
    if not budget.exists():save(budget,dict(started=now(),cap_hours=4))
    if (datetime.datetime.fromisoformat(now())-datetime.datetime.fromisoformat(json.loads(budget.read_text())['started'])).total_seconds()>4*3600:raise RuntimeError('Worker cap reached')
    out=ROOT/'results/raw'/label;out.mkdir(exist_ok=False);start=now();tick=time.monotonic()
    record=dict(label=label,argv=list(map(str,argv)),started=start,binary_sha256=hashlib.sha256((ROOT/'build/causal').read_bytes()).hexdigest(),source_sha256=hashlib.sha256((ROOT/'src/causal.cu').read_bytes()).hexdigest())
    try:
        h=subprocess.run(['nvidia-smi','--query-gpu=timestamp,uuid,temperature.gpu,clocks.sm,power.draw,memory.free,gpu_recovery_action','--format=csv'],capture_output=True,text=True)
        (out/'hardware_before.csv').write_text(h.stdout+h.stderr)
        if h.returncode or 'None' not in h.stdout:raise RuntimeError('GPU health guard')
        p=subprocess.run(record['argv'],env=ENV,capture_output=True,text=True,timeout=1800)
        (out/'stdout.txt').write_text(p.stdout);(out/'stderr.txt').write_text(p.stderr);record['returncode']=p.returncode
        q=subprocess.run(['journalctl','-k','--since',start,'--no-pager'],capture_output=True,text=True)
        (out/'kernel_log.txt').write_text(q.stdout+q.stderr);record['new_xid']=[x for x in q.stdout.splitlines() if 'NVRM: Xid' in x]
        if q.returncode:raise RuntimeError('Kernel journal unavailable')
        if record['new_xid'] or any(x in (p.stdout+p.stderr).lower() for x in ['illegal memory access','illegal instruction','device lost','launch failure']):save(ROOT/'GPU_STOP.json',record);raise RuntimeError('GPU fault; no automatic replay')
        record['status']='PASS' if p.returncode==0 else 'PROCESS_FAILED'
    finally:
        record['finished']=now();record['seconds']=time.monotonic()-tick;save(out/'run.json',record)
        with (ROOT/'results/raw/commands.jsonl').open('a') as f:f.write(json.dumps(record)+'\n')
    print(json.dumps(record),flush=True)
    if p.returncode:raise RuntimeError(p.stderr or p.stdout)
if __name__=='__main__':execute(sys.argv[1],sys.argv[2:])
