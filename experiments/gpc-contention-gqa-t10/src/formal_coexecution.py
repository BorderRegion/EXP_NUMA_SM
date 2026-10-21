import sys
import control_e4
sys.modules['control']=control_e4
from gqa_runtime import *
from gemm_runtime import *
from measure import *
import os,gzip
block=int(sys.argv[1]);folder=Path(os.environ['T10_WORKER_DIR']);c=Control();plan=read(RUN/'freeze/resource_sets.json')['blocks'][block];pilot=read(RUN/'freeze/E4_NATIVE_ONLY_JOB.json');sharedbg=ck(z.gc_primary_stream());bgdata=GemmData(190800000+block*100000);phases=[];rows=[];checks=[];inputs=[dict(task='background',**bgdata.meta)]
all_sms=list(range(56));placements={p['name']:p for p in plan['placements']};placements['NEUTRAL10_46']=plan['neutral']
cases=['GQA4_LONG','BATCH4_RAGGED'];cases=cases[::-1] if block%2 else cases
for cid in cases:
 arg=next(x for x in read(RUN/'freeze/experiment_plan.json')['gqa_cases'] if x['id']==cid);cc=dict(id=cid,B=arg['B'],H=arg['Hq'],HK=arg['Hkv'],D=128,L=max(arg['lengths']),lengths=arg['lengths']);d=GQAData(cc,190900000+block*100000+cc['L'],65536*(block%2));inputs.append(dict(task='foreground',case=cid,**d.meta))
 primary=['SERIAL_GQA_FIRST','SERIAL_GEMM_FIRST','SHARED56','NEUTRAL10_46']+plan['interleaved_order'];order=[('SHARED56','ANCHOR_HEAD'),('SHARED56','AA_HEAD')]+[(x,'PRIMARY') for x in primary]+[('SHARED56_E56','BODY_CONTROL'),('SHARED56','ANCHOR_TAIL'),('SHARED56','AA_TAIL')]
 for phase_index,(policy,role) in enumerate(order):
  phase_setup_start=time.perf_counter()
  if policy in placements:
   p=placements[policy];fs=p['foreground_sm_ids'];bs=p['background_complement_sm_ids'];t=time.perf_counter();fg=c.create(fs);bg=c.create(bs);resource_ms=(time.perf_counter()-t)*1000;c.verify(fg,fs);c.verify(bg,bs)
  else:fg,bg=0,sharedbg;fs=bs=all_sms;resource_ms=0.0
  d.reset();fgjob=GQAJob(d,True,'N19' if fg==0 and policy!='SHARED56_E56' else 'E56');gemm_setup_start=time.perf_counter();bgjob=GemmJob(bgdata,bg);gemm_setup_ms=(time.perf_counter()-gemm_setup_start)*1000;fgs,fg_setup=capture_ring(c,fg,fgjob,32);bgs,bg_setup=capture_ring(c,bg,bgjob,pilot[cid]['bg_gemms']);serial=1 if policy=='SERIAL_GQA_FIRST' else 2 if policy=='SERIAL_GEMM_FIRST' else 0;mix=MixedJob(fgs,bgs,serial)
  phase_setup_ms=(time.perf_counter()-phase_setup_start)*1000
  # Warm the exact fixed job, then sample it without per-job host reference checks.
  total=0.;n=0
  while n<32 or total<50000:
   a=mix.run(4);total+=float(a[:,3].sum());n+=4
  nformal=64 if role in ['PRIMARY','BODY_CONTROL'] else 16;a=mix.run(nformal)
  flast=((nformal-1)%4+31)%4;blast=((nformal-1)%4+pilot[cid]['bg_gemms']-1)%4
  checks.append(dict(case=cid,policy=policy,role=role,task='foreground',**d.check_mode(True,flast)));checks.append(dict(case=cid,policy=policy,role=role,task='background',**bgdata.check(blast)))
  meta=dict(run=RUN.name,stage='E4',block=block,case=cid,mode='APPEND_ATTENTION_PLUS_GEMM',policy=policy,role=role,phase_index=phase_index,foreground_sm_ids=fs,background_sm_ids=bs,sm_set_hash=hashlib.sha256(json.dumps([fs,bs]).encode()).hexdigest(),fg_requests=32,bg_gemms=pilot[cid]['bg_gemms'],input_generation=d.seed,allocation_generation=cid+'_'+str(block),foreground_body='original_N19' if fg==0 and policy!='SHARED56_E56' else 'same_N19_math_without_unused_SM_read',background_body='cuBLAS_GEMM_DEFAULT_TENSOR_OP_FP16_FP32',launcher='green_mixed_v1',state_epoch=utc(),foreground_cta=d.B*d.HK*fgjob.W,foreground_threads=32*d.G,foreground_W=fgjob.W,foreground_fused=fgjob.fused,foreground_shared_bytes=16*(d.D+8)*4+d.G*128*4,background_flops_per_job=bgdata.meta['flops_per_gemm']*pilot[cid]['bg_gemms'],foreground_unique_kv_bytes=2*sum(cc['lengths'])*d.HK*d.D*2,resource_setup_ms=resource_ms,graph_setup_ms=fg_setup+bg_setup,gemm_handle_workspace_setup_ms=gemm_setup_ms,phase_setup_including_diagnostics_ms=phase_setup_ms)
  compact={k:v for k,v in meta.items() if k not in ['foreground_sm_ids','background_sm_ids']}
  for i,x in enumerate(a):rows.append(dict(**compact,sample=i,first_slot=i%4,job_gpu_us=float(x[0]),foreground_completion_us=float(x[1]),background_completion_us=float(x[2]),job_output_ready_us=float(x[3])))
  phases.append(dict(**meta,job_gpu_us=float(a[:,0].mean()),foreground_completion_us=float(a[:,1].mean()),background_completion_us=float(a[:,2].mean()),job_output_ready_us=float(a[:,3].mean()),warmup_jobs=n,warmup_host_us=total,formal_jobs=nformal))
  mix.close();c.graph_drop(fgs);c.graph_drop(bgs);bgjob.close()
  if fg:c.drop(fg);c.drop(bg)
  save_csv(folder/'requests.csv.gz',rows);write(folder/'PHASES.json',phases);write(folder/'NUMERICAL.json',checks)
  print('E4_PHASE',block,cid,policy,role,flush=True)
 d.close();write(folder/'INPUTS.json',inputs)
with gzip.open(folder/'resource_placement.json.gz','wt') as f:json.dump(c.observations,f)
c.drop(sharedbg);write(folder/'COMPLETE.json',dict(status='PASS',block=block,primary_phases=len([p for p in phases if p['role']=='PRIMARY']),sample_jobs=len(rows),checks=len(checks)));print('E4_BLOCK_COMPLETE',block,flush=True)
