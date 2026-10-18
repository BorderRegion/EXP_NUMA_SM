from backend import *

def conditioning(e,out,seconds=60):
 d=Data(256,1024,4096,seed=991,ring=1);j=Job(e,d,kind=3);j.run();start=time.monotonic();count=0
 while time.monotonic()-start<seconds:j.batch(256);count+=256
 append(out/'conditioning.jsonl',dict(started=utc(),wall_s=time.monotonic()-start,replays=count,kind='USEFUL_CUBLAS_GEMM',shape=[256,1024,4096]));j.close();d.close()

def phase(out,e,d,identity,kwargs,requests=64,replays=256,warm_ms=100,check_bitwise=None):
 t0=time.time_ns();jobs=[];checks=[]
 for slot in range(d.ring):jobs.append(Job(e,d,slot=slot,**kwargs))
 for j in jobs:j.run();checks.append(d.numerical(j.slot,j.alpha,j.beta))
 # Warm every actual graph, then reach a common minimum 100 ms of measured batches.
 warmed=0.;wn=0
 for j in jobs:
  a=j.batch(8);warmed+=a[0]/1000;wn+=8
 while warmed<warm_ms or wn<32:
  estimate=max(1e-6,a[0]/1000/max(8 if wn<=d.ring*8 else step,1))
  step=max(32-wn,min(256,max(1,math.ceil((warm_ms-warmed)/estimate))))
  step=max(1,step);a=jobs[0].batch(step);warmed+=a[0]/1000;wn+=step
 records=[]
 for req in range(requests):
  j=jobs[req%d.ring];cpu_start=time.perf_counter_ns();values=j.run();outer_cpu=(time.perf_counter_ns()-cpu_start)/1000
  records.append(dict(request=req,input_slot=j.slot,workspace_generation=req+1,gpu_us=values[0],cpu_cpp_us=values[1],cpu_ready_us=outer_cpu,P_us=values[2] if values[2]>=0 else None,R_us=values[3] if values[3]>=0 else None,scratch_us=values[4] if values[4]>=0 else None))
  if req in [0,requests//2,requests-1]:
   check=d.numerical(j.slot,j.alpha,j.beta);check['request']=req;checks.append(check)
   if check_bitwise is not None:
    bits=d.d.cpu().numpy().view('uint32');expected=check_bitwise[j.slot]
    expected_first=expected['first'] if isinstance(expected,dict) else expected
    if not np.array_equal(bits,expected_first):raise RuntimeError('phase raw-bit mismatch')
    if d.chain and not np.array_equal(d.d2.cpu().numpy().view('uint32'),expected['chain']):raise RuntimeError('phase final-chain raw-bit mismatch')
 batch=jobs[0].batch(replays);checks.append(d.numerical(0,kwargs.get('alpha',1),kwargs.get('beta',0)))
 row=dict(**identity,shape=[d.m,d.n,d.k],seed=d.seed,S=kwargs.get('s',2),actual_split_count=None if kwargs.get('kind',0)==3 else 1 if kwargs.get('kind',0)==4 else kwargs.get('s',2),library_internal_split='UNKNOWN' if kwargs.get('kind',0)==3 else 'EXPLICIT',recipe=kwargs.get('recipe',0),layout='TILE_SLAB' if kwargs.get('slab',0) else 'PLANAR',config=jobs[0].cfg,workspace_address=d.w.data_ptr()+kwargs.get('wslot',0)*d.wsize*4,workspace_capacity_bytes=d.w.numel()*4,formal_diagnostic=kwargs.get('diag',0),gpu_us=float(np.mean([x['gpu_us'] for x in records])),cpu_ready_us=float(np.mean([x['cpu_ready_us'] for x in records])),batch_per_replay_us=batch[0]/replays,batch_span_ms=batch[0]/1000,batch_replays=replays,warmup_replays=wn,warmup_gpu_ms=warmed,request_count=requests,graph_build_ms=sum(j.build_ms for j in jobs),substantive_kernels=jobs[0].nodes[0],body_graph_nodes=jobs[0].nodes[1],actual_dag=jobs[0].dag,wall_start_ns=t0,wall_end_ns=time.time_ns(),status='PASS')
 for k in ['P_us','R_us','scratch_us']:
  a=[x[k] for x in records if x[k] is not None];row[k]=float(np.mean(a)) if a else None
 append(out/'phases.jsonl',row);append(out/'samples.jsonl',dict(phase_id=identity['phase_id'],records=records));append(out/'correctness.jsonl',dict(phase_id=identity['phase_id'],checks=checks))
 for j in jobs:j.close()
 return row

def qualification(e,d,kwargs,out,label):
 j=Job(e,d,slot=0,**kwargs);j.run();a=d.numerical(0);bits={0:d.d.cpu().numpy().view('uint32').copy()};j.close()
 for slot in range(1,d.ring):
  j=Job(e,d,slot=slot,**kwargs);j.run();d.numerical(slot);bits[slot]=d.d.cpu().numpy().view('uint32').copy();j.close()
 if d.chain:
  # Preserve both the first GEMM and the downstream final output bit patterns.
  for slot in range(d.ring):
   j=Job(e,d,slot=slot,**kwargs);j.run();d.numerical(slot);bits[slot]=dict(first=bits[slot],chain=d.d2.cpu().numpy().view('uint32').copy());j.close()
 append(out/'qualifications.jsonl',dict(label=label,reference=a,scope='complete output every input-ring slot; bitwise references retained in process'))
 return bits
