"""One explicitly authorized bounded retry. Never re-run an existing attempt."""
from pathlib import Path
import csv, datetime, hashlib, json, os, subprocess, time

root = Path(__file__).resolve().parents[1]
attempt = 'fixed_queue_retry_20261013T0928Z'
outbase = root / 'results/raw' / attempt
outbase.mkdir(exist_ok=False)
started = datetime.datetime.now().astimezone()
clock = time.monotonic()
records = []
state = {
    'attempt': attempt, 'started': started.isoformat(),
    'authorization': 'User: Retry the fixed executor',
    'scope': 'Four small-image checks, then one Bonsai 1080p check; stop on any failure. Resume original experiments only if all pass.',
    'prior_worker_hours': 0.31444444444444447,
    'binary_sha256': hashlib.sha256((root/'build/native/scheduled_renderer').read_bytes()).hexdigest(),
    'source_sha256': hashlib.sha256((root/'src/core/forward.cu').read_bytes()).hexdigest(),
    'checks': records, 'state': 'RUNNING',
}
def write():
    state['elapsed_seconds'] = time.monotonic()-clock
    (outbase/'RESULT.json').write_text(json.dumps(state, indent=2)+'\n')
def journal():
    p = subprocess.run(['journalctl','-k','--since',started.isoformat(),'--no-pager'],capture_output=True,text=True)
    if p.returncode:
        raise RuntimeError('Cannot inspect kernel log: '+p.stderr)
    (outbase/'kernel_log.txt').write_text(p.stdout)
    return [line for line in p.stdout.splitlines() if 'NVRM: Xid' in line]
def telemetry(name):
    p = subprocess.run(['nvidia-smi','--query-gpu=timestamp,name,temperature.gpu,memory.free,memory.total,gpu_recovery_action','--format=csv'],capture_output=True,text=True)
    (outbase/f'{name}_telemetry.txt').write_text(p.stdout+p.stderr)
    if p.returncode or 'None' not in p.stdout:
        raise RuntimeError('Telemetry/recovery action guard failed')
    return p.stdout
write()
env = os.environ.copy()
env['LD_LIBRARY_PATH'] = str(root/'offline_inbox/toolchain/cuda-13.2/lib')+':'+env.get('LD_LIBRARY_PATH','')
try:
    telemetry('before')
    journal()
    for scene,w,h,policy in [('bonsai',320,180,1),('bonsai',320,180,6),('train',640,360,1),('train',640,360,6),('bonsai',1920,1080,1)]:
        label=f'{scene}_{w}x{h}_Q{policy}'
        out=outbase/label
        ref=root/'results/raw/recovery_20261013T074618Z/executor_checks_r2'/f'{scene}_{w}x{h}_native'
        cmd=[str(root/'build/native/scheduled_renderer'),str(root/'offline_inbox/assets'/scene),str(w),str(h),'0','3',str(out),'8',str(policy),'1']
        before=time.monotonic()
        p=subprocess.run(cmd,env=env,capture_output=True,text=True,timeout=120)
        out.mkdir(exist_ok=True)
        (out/'stdout.txt').write_text(p.stdout)
        (out/'stderr.txt').write_text(p.stderr)
        rec={'label':label,'argv':cmd,'returncode':p.returncode,'wall_seconds':time.monotonic()-before}
        records.append(rec)
        rec['new_xid_events']=journal()
        write()
        if p.returncode or rec['new_xid_events']:
            raise RuntimeError(f'{label}: GPU/process failure; no more GPU work. '+p.stderr)
        rec['raw_sha256']={f:hashlib.sha256((out/f).read_bytes()).hexdigest() for f in ['color.raw','final_T.raw','n_contrib.raw']}
        rec['reference_sha256']={f:hashlib.sha256((ref/f).read_bytes()).hexdigest() for f in rec['raw_sha256']}
        rec['full_first_frame_bitwise_equal']=rec['raw_sha256']==rec['reference_sha256']
        def hashes(path):
            with (path/'frames.csv').open() as f:
                return [(r['camera'],r['color_hash'],r['finite']) for r in csv.DictReader(f)]
        rec['all_three_color_hashes_equal']=hashes(out)==hashes(ref)
        write()
        if not rec['full_first_frame_bitwise_equal'] or not rec['all_three_color_hashes_equal']:
            raise RuntimeError(f'{label}: correctness failure')
        telemetry(label)
        print(label,'PASS',flush=True)
    state['state']='PASS'
    state['resumption_authorized']=True
except Exception as error:
    state['state']='STOPPED'
    state['failure']=str(error)
    print('STOPPED:',error,flush=True)
finally:
    state['finished']=datetime.datetime.now().astimezone().isoformat()
    state['total_worker_hours']=state['prior_worker_hours']+(time.monotonic()-clock)/3600
    write()
    print(json.dumps({'state':state['state'],'checks':len(records),'elapsed_seconds':state['elapsed_seconds']}),flush=True)
if state['state']!='PASS':
    raise SystemExit(2)
