"""One local worker; shares the original campaign's lock, with separate accounting."""
import datetime, fcntl, hashlib, json, os, pathlib, shutil, subprocess, sys, time, uuid
from frozen_source import freeze
ROOT = pathlib.Path(__file__).resolve().parents[1]
PARENT = ROOT.parent
CAPS = {x:14400 for x in ['S1','S2','S3','S4']}
RUN_ROOT=pathlib.Path(os.environ['SAME_Q_V2_RUN'])
STATE=json.loads((RUN_ROOT/'RUN_STATE.json').read_text())
OLD_PREFIX=92
DEADLINE=datetime.datetime.fromisoformat(STATE['hard_deadline'])
def utc(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p): return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def run(stage, key, script, args=()):
    registry=ROOT/'registry/runs.jsonl'
    rows=[json.loads(x) for x in registry.read_text().splitlines()] if registry.exists() else []
    old=[x for x in rows if x['key']==key]
    if old:
        print('EXISTING',key,old[-1]['status'],flush=True); return old[-1]
    rid=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+uuid.uuid4().hex[:8]
    out=ROOT/'runs'/rid;out.mkdir()
    m=dict(run_id=rid,key=key,stage=stage,status='REQUESTED',requested_at=utc(),platform='t10',
           campaign='T10_SAME_Q_AND_BACKBONE_V2',source_sha256=sha(script),
           protocol_sha256=sha(RUN_ROOT/'PROTOCOL_V2.json'),path=str(out.relative_to(ROOT)))
    command=[sys.executable,str(script),*map(str,args),'--out',str(out)]
    m['command']=command
    def save(): (out/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2))
    save()
    with open(PARENT/'environment/gpu_worker.lock','a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        m['lock_acquired_at']=utc();start=time.monotonic()
        rows=[json.loads(x) for x in registry.read_text().splitlines()] if registry.exists() else []
        used=sum(x['worker_occupied_s'] for x in rows)
        stageused=sum(x['worker_occupied_s'] for x in rows[OLD_PREFIX:])
        remaining=min(57600-used,14400-stageused,(DEADLINE-datetime.datetime.now(datetime.timezone.utc)).total_seconds()-1800)
        if remaining<=0:raise RuntimeError('V2 budget/end-of-work report reserve reached')
        if used>=57600 or stageused>=14400: raise RuntimeError('Worker budget exhausted')
        if any(p.exists() for p in [PARENT/'environment/GPU_HEALTH_STOP', ROOT/'registry/GPU_HEALTH_STOP']): raise RuntimeError('GPU health stop')
        if shutil.disk_usage(ROOT).free<2*2**30: raise RuntimeError('Disk reserve exhausted')
        query=['nvidia-smi','--query-gpu=uuid,name,driver_version,memory.total,memory.free,temperature.gpu,power.limit,ecc.errors.uncorrected.volatile.total','--format=csv']
        before=subprocess.check_output(query,text=True);(out/'device_before.csv').write_text(before)
        env=os.environ.copy();env.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_DATASETS_OFFLINE='1',TOKENIZERS_PARALLELISM='false',OMP_NUM_THREADS='2',MKL_NUM_THREADS='2',MAX_JOBS='2',TORCHINDUCTOR_COMPILE_THREADS='2',TRITON_CACHE_DIR=str(ROOT/'build/t10/triton_cache'),OP_FUSED_REMAINING_S=str(remaining))
        frozen_entry, frozen_records=freeze(ROOT,script,out/'frozen'/'op-fused')
        source_bytes=frozen_entry.read_bytes()
        m['requested_source_sha256']=m['source_sha256']
        m['source_sha256']=hashlib.sha256(source_bytes).hexdigest()
        (out/'source_snapshot.py').write_bytes(source_bytes)
        m['requested_command']=command
        command=[sys.executable,str(frozen_entry),*map(str,args),'--out',str(out)]
        m['command']=command
        m['executed_source_scope']='READ_ONLY_LOCAL_SOURCE_TREE; installed libraries locked separately'
        m['frozen_source_manifest']=str((out/'frozen/op-fused/FROZEN_SOURCE_MANIFEST.json').relative_to(out))
        env['PYTHONDONTWRITEBYTECODE']='1'
        inp=out/'input';inp.mkdir()
        for name in ['PROTOCOL_V2.json','cases_v2.json','BODY_AND_BASELINE_FREEZE_V2.json']:
            source=RUN_ROOT/name
            if source.exists():shutil.copyfile(source,inp/name)
        command.extend(['--run-root',str(inp)])
        m['command']=command
        with open(out/'telemetry.csv','w') as telemetry,open(out/'stdout.log','w') as stdout,open(out/'stderr.log','w') as stderr:
            mon=subprocess.Popen(['nvidia-smi','--query-gpu=timestamp,uuid,temperature.gpu,clocks.sm,power.draw,memory.used,utilization.gpu,clocks_event_reasons.active,power.limit,enforced.power.limit','--format=csv','-l','1'],stdout=telemetry,stderr=telemetry)
            m['process_started_at']=utc();m['status']='RUNNING';p=subprocess.Popen(command,stdout=stdout,stderr=stderr,env=env)
            m['pid']=p.pid;save()
            try:
                rc=p.wait(timeout=max(1,remaining-(time.monotonic()-start)))
            except subprocess.TimeoutExpired:
                m['budget_timeout']=True;p.terminate()
                try:rc=p.wait(timeout=5)
                except subprocess.TimeoutExpired:p.kill();rc=p.wait()
            m['process_ended_at']=utc();mon.terminate();mon.wait()
        m.update(returncode=rc,status='COMPLETED' if rc==0 else 'FAILED',worker_occupied_s=time.monotonic()-start)
        errors=(out/'stderr.log').read_text()
        if any(t in errors for t in ['illegal memory access','device-side assert','device lost','CUDA_ERROR_UNKNOWN','unspecified launch failure']):
            (ROOT/'registry/GPU_HEALTH_STOP').write_text(rid+'\n'+errors)
        (out/'device_after.csv').write_text(subprocess.check_output(query,text=True))
        m['worker_occupied_s']=time.monotonic()-start
        m['released_at']=utc();save()
        if rc==0: (out/'COMPLETE').write_text(m['released_at'])
        with registry.open('a') as f:f.write(json.dumps(m,ensure_ascii=False)+'\n')
    print(key,m['status'],round(m['worker_occupied_s'],3),str(out),flush=True)
    return m
if __name__=='__main__': run(sys.argv[1],sys.argv[2],pathlib.Path(sys.argv[3]).resolve(),sys.argv[4:])
