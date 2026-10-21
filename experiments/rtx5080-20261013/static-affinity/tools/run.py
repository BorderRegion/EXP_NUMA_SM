from pathlib import Path
import datetime,json,os,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[1]
OLD=ROOT.parent/'affinity-render-5080'
ENV=os.environ.copy()
ENV['LD_LIBRARY_PATH']=str(OLD/'offline_inbox/toolchain/cuda-13.2/lib')+':'+ENV.get('LD_LIBRARY_PATH','')
def now():return datetime.datetime.now().astimezone().isoformat()
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def execute(label,phase,argv,gpu=True,timeout=1800):
    if gpu and (ROOT/'GPU_STOP.json').exists():raise RuntimeError('GPU stop active')
    out=ROOT/'results/raw'/label;out.mkdir(exist_ok=False)
    start=now();tick=time.monotonic()
    record={'label':label,'phase':phase,'argv':list(map(str,argv)),'started':start,'gpu_worker_reserved':gpu}
    budget=ROOT/'worker_start.json'
    if gpu and not budget.exists():save(budget,{'started':start,'cap_hours':24})
    if gpu and (datetime.datetime.fromisoformat(start)-datetime.datetime.fromisoformat(json.loads(budget.read_text())['started'])).total_seconds()>24*3600:raise RuntimeError('Worker cap reached')
    try:
        if gpu:
            p=subprocess.run(['nvidia-smi','--query-gpu=timestamp,uuid,temperature.gpu,clocks.sm,power.draw,memory.free,gpu_recovery_action','--format=csv'],capture_output=True,text=True)
            (out/'hardware_before.csv').write_text(p.stdout+p.stderr)
            if p.returncode or 'None' not in p.stdout:raise RuntimeError('GPU health guard')
        p=subprocess.run(record['argv'],env=ENV,text=True,capture_output=True,timeout=timeout)
        (out/'stdout.txt').write_text(p.stdout);(out/'stderr.txt').write_text(p.stderr);record['returncode']=p.returncode
        if gpu:
            q=subprocess.run(['journalctl','-k','--since',start,'--no-pager'],capture_output=True,text=True)
            (out/'kernel_log.txt').write_text(q.stdout+q.stderr)
            record['xid_events']=[s for s in q.stdout.splitlines() if 'NVRM: Xid' in s]
            if q.returncode:raise RuntimeError('Kernel log not readable')
            if record['xid_events'] or any(s in p.stderr.lower() for s in ['illegal instruction','illegal memory access','device lost','launch failure']):
                save(ROOT/'GPU_STOP.json',record);raise RuntimeError('GPU fault: stop, no automatic replay')
        record['status']='PASS' if p.returncode==0 else 'PROCESS_FAILED'
    finally:
        record['finished']=now();record['seconds']=time.monotonic()-tick
        save(out/'run.json',record)
        with (ROOT/'results/raw/commands.jsonl').open('a') as f:f.write(json.dumps(record)+'\n')
    print(json.dumps(record),flush=True)
    if p.returncode:raise RuntimeError(p.stderr or p.stdout)
    return out
if __name__=='__main__':execute(sys.argv[1],sys.argv[2],sys.argv[3:])
