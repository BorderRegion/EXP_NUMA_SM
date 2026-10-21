from pathlib import Path
import datetime, hashlib, json, os, subprocess, time

ROOT=Path(__file__).resolve().parents[1]
META=json.loads((ROOT/'experiment/run.json').read_text())
RAW=ROOT/'results/raw'/META['run_id']
RAW.mkdir(exist_ok=True)
ENV=os.environ.copy()
ENV['LD_LIBRARY_PATH']=str(ROOT/'offline_inbox/toolchain/cuda-13.2/lib')+':'+ENV.get('LD_LIBRARY_PATH','')
def stamp(): return datetime.datetime.now().astimezone().isoformat()
def save(path, data): path.write_text(json.dumps(data,indent=2)+'\n')
def run(label, argv, phase, timeout=900):
    if (ROOT/'recovery/GPU_STOP.json').exists(): raise RuntimeError('GPU stop is active')
    out=RAW/label
    out.mkdir(exist_ok=False)
    start=stamp(); tick=time.monotonic()
    rec={'label':label,'phase':phase,'started':start,'argv':[str(x) for x in argv],'output':str(out)}
    save(out/'run.json',rec)
    try:
        p=subprocess.run(['nvidia-smi','--query-gpu=timestamp,uuid,temperature.gpu,clocks.sm,clocks.mem,power.draw,memory.used,memory.free,gpu_recovery_action','--format=csv'],capture_output=True,text=True)
        (out/'hardware_before.csv').write_text(p.stdout)
        if p.returncode or 'None' not in p.stdout: raise RuntimeError('GPU telemetry guard')
        p=subprocess.run(rec['argv'],env=ENV,capture_output=True,text=True,timeout=timeout)
        (out/'stdout.txt').write_text(p.stdout);(out/'stderr.txt').write_text(p.stderr)
        rec['returncode']=p.returncode
        log=subprocess.run(['journalctl','-k','--since',start,'--no-pager'],capture_output=True,text=True)
        (out/'kernel_log.txt').write_text(log.stdout+log.stderr)
        rec['new_xid_events']=[s for s in log.stdout.splitlines() if 'NVRM: Xid' in s]
        if log.returncode: raise RuntimeError('Kernel log unavailable')
        if p.returncode or rec['new_xid_events']: raise RuntimeError('Process failed or new GPU fault: '+p.stderr)
        p=subprocess.run(['nvidia-smi','--query-gpu=timestamp,uuid,temperature.gpu,clocks.sm,clocks.mem,power.draw,memory.used,memory.free,gpu_recovery_action','--format=csv'],capture_output=True,text=True)
        (out/'hardware_after.csv').write_text(p.stdout)
        if p.returncode or 'None' not in p.stdout: raise RuntimeError('Post-run telemetry guard')
        rec['status']='PASS'
    except Exception as e:
        rec['status']='STOPPED';rec['error']=str(e)
        save(ROOT/'recovery/GPU_STOP.json',rec)
        raise
    finally:
        rec['finished']=stamp();rec['worker_seconds']=time.monotonic()-tick
        save(out/'run.json',rec)
        with (RAW/'commands.jsonl').open('a') as f:f.write(json.dumps(rec)+'\n')
        print(label,rec['status'],round(rec['worker_seconds'],2),'s',flush=True)
    return out
def bench(label, scene, track, settings, frames, warm, seconds, mode, executor=1, W=1920,H=1080,phase=None):
    argv=[ROOT/'build/native/benchmark',ROOT/'offline_inbox/assets'/scene,W,H,track,settings,frames,warm,seconds,RAW/label,mode,executor]
    return run(label,argv,phase or mode)

if __name__=='__main__':
    for rep in range(3): run(f'micro_{rep}',[ROOT/'build/micro',RAW/f'micro_{rep}'],'E1_E2')
