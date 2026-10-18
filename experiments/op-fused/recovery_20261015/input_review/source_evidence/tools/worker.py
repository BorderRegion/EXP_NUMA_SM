"""One local worker; shares the original campaign's lock, with separate accounting."""
import datetime, fcntl, hashlib, json, os, pathlib, shutil, subprocess, sys, time, uuid
ROOT = pathlib.Path(__file__).resolve().parents[1]
PARENT = ROOT.parent
CAPS = dict(E0=1800,E1=5400,E2=7200,E3=14400,E4=9000,E5=7200,E6=5400,E7=7200)
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
           campaign='OPERATOR_FUSED_SCHEDULING_DUAL_20261015',source_sha256=sha(script),
           protocol_sha256=sha(ROOT/'protocol/configs/campaign.json'),path=str(out.relative_to(ROOT)))
    command=[sys.executable,str(script),*map(str,args),'--out',str(out)]
    m['command']=command
    def save(): (out/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2))
    save()
    with open(PARENT/'environment/gpu_worker.lock','a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        m['lock_acquired_at']=utc();start=time.monotonic()
        rows=[json.loads(x) for x in registry.read_text().splitlines()] if registry.exists() else []
        used=sum(x['worker_occupied_s'] for x in rows)
        stageused=sum(x['worker_occupied_s'] for x in rows if x['stage']==stage)
        if used>=57600 or stageused>=CAPS[stage]: raise RuntimeError('Worker budget exhausted')
        if any(p.exists() for p in [PARENT/'environment/GPU_HEALTH_STOP', ROOT/'registry/GPU_HEALTH_STOP']): raise RuntimeError('GPU health stop')
        if shutil.disk_usage(ROOT).free<2*2**30: raise RuntimeError('Disk reserve exhausted')
        query=['nvidia-smi','--query-gpu=uuid,name,driver_version,memory.total,memory.free,temperature.gpu,power.limit,ecc.errors.uncorrected.volatile.total','--format=csv']
        before=subprocess.check_output(query,text=True);(out/'device_before.csv').write_text(before)
        env=os.environ.copy();env.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_DATASETS_OFFLINE='1',TOKENIZERS_PARALLELISM='false',OMP_NUM_THREADS='2',MKL_NUM_THREADS='2',MAX_JOBS='2',TORCHINDUCTOR_COMPILE_THREADS='2',TRITON_CACHE_DIR=str(ROOT/'build/t10/triton_cache'),OP_FUSED_REMAINING_S=str(min(57600-used,CAPS[stage]-stageused)))
        source_bytes=pathlib.Path(script).read_bytes()
        m['requested_source_sha256']=m['source_sha256']
        m['source_sha256']=hashlib.sha256(source_bytes).hexdigest()
        (out/'source_snapshot.py').write_bytes(source_bytes)
        with open(out/'telemetry.csv','w') as telemetry,open(out/'stdout.log','w') as stdout,open(out/'stderr.log','w') as stderr:
            mon=subprocess.Popen(['nvidia-smi','--query-gpu=timestamp,uuid,temperature.gpu,clocks.sm,power.draw,memory.used,utilization.gpu,clocks_event_reasons.active,power.limit,enforced.power.limit','--format=csv','-l','1'],stdout=telemetry,stderr=telemetry)
            m['process_started_at']=utc();m['status']='RUNNING';p=subprocess.Popen(command,stdout=stdout,stderr=stderr,env=env)
            m['pid']=p.pid;save();rc=p.wait();m['process_ended_at']=utc();mon.terminate();mon.wait()
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
