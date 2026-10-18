import pathlib,json,datetime,uuid,subprocess,time,hashlib,fcntl,os
ROOT=pathlib.Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def decision(ident,text,**kw):
 with open(ROOT/'DECISIONS.jsonl','a') as f:f.write(json.dumps(dict(timestamp_utc=utc(),id=ident,decision=text,**kw),ensure_ascii=False)+'\n')
def run(stage,config,args,*,executable='micro_runner',build=None):
 build=pathlib.Path(build or ROOT/'build/current').resolve();rid='t10_'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+uuid.uuid4().hex[:8]
 p=ROOT/'runs/t10'/stage/rid;p.mkdir(parents=True,exist_ok=False)
 cmd=[str(build/executable),*map(str,args),'--out',str(p)]
 if executable=='micro_runner':cmd+=['--cubin',str(build/'micro.cubin')]
 manifest=dict(schema_version='1.0',run_id=rid,parent_run_id=config.get('parent_run'),platform='t10',stage=stage,status='PLANNED',build_id=build.name,config=config,command=cmd,start_utc=utc(),actual_cost=0,cost_unit='CNY',cost_basis='User reports local owned hardware with no resource charge; electricity not metered',protocol_sha256=sha(ROOT/'GPU_COMPUTE_TOPOLOGY_DUAL_20261014/campaign.json'),local_protocol_sha256=sha(ROOT/'preregistration/LOCAL_PROTOCOL.md'),build_ref=str(build.relative_to(ROOT)/'build.json'),device_query_ref='environment/device_query.json')
 (p/'config.resolved.json').write_text(json.dumps(config,indent=2));(p/'manifest.json').write_text(json.dumps(manifest,indent=2))
 with open(ROOT/'environment/gpu_worker.lock','w') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  if (ROOT/'environment/GPU_HEALTH_STOP').exists():raise RuntimeError('GPU health stop marker exists')
  health=subprocess.run(['nvidia-smi','--query-gpu=temperature.gpu,clocks.sm,clocks.mem,power.draw,memory.used,utilization.gpu','--format=csv,noheader,nounits'],capture_output=True,text=True)
  (p/'health_before.csv').write_text(health.stdout+health.stderr)
  if health.returncode:raise RuntimeError('Device health query failed')
  t=time.perf_counter()
  with open(p/'stdout.log','w') as o,open(p/'stderr.log','w') as e:
   proc=subprocess.run(cmd,stdout=o,stderr=e)
  manifest.update(end_utc=utc(),worker_seconds=time.perf_counter()-t,returncode=proc.returncode,status='SUCCESS' if proc.returncode==0 else 'FAILED')
  errors=(p/'stderr.log').read_text();manifest['failure_reason']=errors.strip() or None
  if any(s in errors for s in ['CUDA_ERROR_LAUNCH_FAILED','CUDA_ERROR_ECC_UNCORRECTABLE','CUDA_ERROR_GPU_IS_LOST','CUDA_ERROR_UNKNOWN','device-side assert']):
   (ROOT/'environment/GPU_HEALTH_STOP').write_text(rid+'\n'+errors)
  health=subprocess.run(['nvidia-smi','--query-gpu=temperature.gpu,clocks.sm,clocks.mem,power.draw,memory.used,utilization.gpu','--format=csv,noheader,nounits'],capture_output=True,text=True);(p/'health_after.csv').write_text(health.stdout+health.stderr)
 (p/'manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
 with open(ROOT/'run_index.jsonl','a') as f:f.write(json.dumps(dict(run_id=rid,path=str(p.relative_to(ROOT)),**{k:manifest[k] for k in ['stage','status','build_id','worker_seconds','start_utc','end_utc']},config=config),ensure_ascii=False)+'\n')
 print(stage,rid,manifest['status'],errors.strip()[:200],flush=True)
 return p,manifest
