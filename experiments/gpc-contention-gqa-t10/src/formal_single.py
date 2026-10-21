from gqa_runtime import *
from micro_runtime import Micro
from measure import *
import os,sys,gzip
stage=sys.argv[1];block=int(sys.argv[2]);folder=Path(os.environ['T10_WORKER_DIR']);c=Control();rows=[];phases=[];checks=[];setups=[];inputs=[]
plan=read(RUN/'freeze/resource_sets.json')['blocks'][block];pilot=read(RUN/'freeze/PILOT_BATCH.json')
resources={'N19':0,'E56':c.create(list(range(56)))};members={'N19':list(range(56)),'E56':list(range(56))}
for p in plan['placements']:
 resources[p['name']]=c.create(p['foreground_sm_ids']);members[p['name']]=p['foreground_sm_ids']
for name,g in resources.items():c.verify(g,members[name])
if stage=='E2':cases=[(recipe,grid) for recipe in ['HOT2_DEFAULT','HOT2_CG','STREAM32_DEFAULT','STREAM32_CG','STREAM128_CG','REG_FMA'] for grid in [40,160]]
else:cases=[(x,append) for x in read(RUN/'freeze/experiment_plan.json')['gqa_cases'] for append in [False,True]]
cases=cases[block%len(cases):]+cases[:block%len(cases)]
for suite_index,(arg,mode) in enumerate(cases):
 t=time.perf_counter();seed=190200000+block*100000+suite_index*1000
 if stage=='E2':
  data=Micro(arg,mode,seed);case=arg+'_'+str(mode);batch=pilot['micro'][case]['batch'];anchor='E56';primary=['E56']+plan['interleaved_order'];cfg=dict(cta=mode,threads=128,shared_bytes=0,unique_input_bytes=data.nbytes,passes=data.passes,logical_requested_load_bytes=data.nbytes*data.passes if not data.compute else 1024,algorithm='REG_FMA_8x128' if data.compute else '16B_grid_stride')
  inputs.append(dict(case=case,seed=seed,hashes=[hashlib.sha256((data.host+(s if not data.compute else s*.125)).tobytes()).hexdigest() for s in range(4)],addresses=[v.data_ptr() for v in data.inputs]))
 else:
  cc=dict(id=arg['id'],B=arg['B'],H=arg['Hq'],HK=arg['Hkv'],D=arg['D'],L=max(arg['lengths']),lengths=arg['lengths']);data=GQAData(cc,seed,65536*(block%2));case=arg['id']+'_'+str(int(mode));batch=pilot['gqa'][case]['batch'];anchor='N19';primary=['N19','E56']+plan['interleaved_order'];tmp=GQAJob(data,mode,'E56');cfg=dict(cta=data.B*data.HK*tmp.W,threads=32*data.G,shared_bytes=16*(data.D+8)*4+data.G*128*4,W=tmp.W,fused=tmp.fused,route=tmp.policy,unique_kv_bytes=2*sum(cc['lengths'])*data.HK*data.D*2,mode='APPEND_ATTENTION' if mode else 'ATTENTION_ONLY',legacy_blind_page_lists_retained=bool(tmp.mode),no_new_SM_or_address_preference=True);inputs.append(dict(case=case,**data.meta))
 setups.append(dict(case=case,data_setup_ms=(time.perf_counter()-t)*1000))
 order=[(anchor,'ANCHOR_HEAD'),(anchor,'AA_HEAD')]+[(p,'PRIMARY') for p in primary]+[(anchor,'ANCHOR_TAIL'),(anchor,'AA_TAIL')]
 for phase_index,(policy,role) in enumerate(order):
  g=resources[policy]
  if stage=='E3':data.reset();job=GQAJob(data,mode,'N19' if policy=='N19' else 'E56')
  else:job=data
  meta=dict(run=RUN.name,stage=stage,block=block,case=case,mode=cfg.get('mode','MICRO'),policy=policy,role=role,suite_index=suite_index,phase_index=phase_index,sm_set_hash=hashlib.sha256(json.dumps(members[policy]).encode()).hexdigest(),sm_ids=members[policy],input_generation=seed,allocation_generation=case+'_'+str(block),math_body='original_N19' if policy=='N19' else 'micro_v1' if stage=='E2' else 'N19_math_no_unused_SM_preference',launcher='green_graph_v1',state_epoch=utc(),**{k:v for k,v in cfg.items() if k!='mode'})
  graphs,setup=capture_ring(c,g,job,1)
  for slot in range(4):
   c.run([graphs[slot]],1);q=data.check(slot) if stage=='E2' else data.check_mode(mode,slot)
   checks.append(dict(case=case,policy=policy,role=role,slot=slot,**q))
  for view,factor in [('single',1),('batch',batch)]:
   if factor==1:gg=graphs;setup_ms=setup
   else:gg,setup_ms=capture_ring(c,g,job,factor)
   n=64 if role=='PRIMARY' else 16
   # Keep auxiliary counts divisible by the baseline-selected batch size.
   n=max(n,factor)
   a,w=measure(c,gg,factor,n);last=((n//factor-1)%4+factor-1)%4
   q=data.check(last) if stage=='E2' else data.check_mode(mode,last)
   checks.append(dict(case=case,policy=policy,role=role,view=view,slot=last,**q))
   compact={k:v for k,v in meta.items() if k!='sm_ids'}
   for i,(gpu,host) in enumerate(a):rows.append(dict(**compact,view=view,batch=factor,sample=i,first_input_slot=i%4,gpu_span_us=float(gpu),output_ready_us=float(host),gpu_per_request_us=float(gpu/factor),host_per_request_us=float(host/factor),setup_ms=setup_ms))
   phases.append(dict(**meta,view=view,batch=factor,requests=n,gpu_per_request_us=float(np.mean(a[:,0])/factor),host_per_request_us=float(np.mean(a[:,1])/factor),setup_ms=setup_ms,warmup=w))
   if factor!=1:c.graph_drop(gg)
  c.graph_drop(graphs)
  save_csv(folder/'requests.csv.gz',rows);write(folder/'PHASES.json',phases);write(folder/'NUMERICAL.json',checks)
 print('SUITE_COMPLETE',stage,block,case,flush=True)
 if stage=='E3':data.close()
 else:del data;gc.collect();torch.cuda.empty_cache()
 write(folder/'INPUTS.json',inputs);write(folder/'SETUP.json',setups)
with gzip.open(folder/'resource_placement.json.gz','wt') as f:json.dump(c.observations,f)
for name,g in resources.items():
 if g:c.drop(g)
write(folder/'COMPLETE.json',dict(status='PASS',stage=stage,block=block,primary_phases=len([x for x in phases if x['role']=='PRIMARY' and x['view']=='single']),views=len(phases),requests=len(rows),numerical_checks=len(checks)));print('BLOCK_COMPLETE',stage,block,flush=True)
