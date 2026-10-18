from backend import *

def conditioning(e,out,seconds=60):
 d=Data(256,1024,4096,ring=1);j=Job(e,d,kind=3);j.run();t=time.monotonic();reps=0
 while time.monotonic()-t<seconds:j.batch(128);reps+=128
 append(out/'conditioning.jsonl',dict(wall_s=time.monotonic()-t,replays=reps,shape=[256,1024,4096],kind='USEFUL_NATIVE_GEMM'));j.close();d.close()

def pilot(e,d,out,cid,cap=128):
 j=Job(e,d,kind=3,s=1);j.batch(8);a=j.batch(16);cpu=a[1]/16;gpu=a[0]/16;j.close();n=max(8,min(cap,math.ceil(200000/max(cpu,1e-6))))
 append(out/'pilots.jsonl',dict(case=cid,lib_cpu_batch_us=cpu,lib_gpu_batch_us=gpu,requests=n,cap=cap));return n

def phase(e,d,out,identity,kw,requests,batch_replays=None,warm_ms=20,check_bits=None):
 budget_check();start=time.time_ns();jobs=[Job(e,d,slot=s,**kw) for s in range(d.ring)];build_ms=sum(j.build_ms for j in jobs);warm=0.;wn=0
 for j in jobs:
  v=j.batch(2);warm+=v[0]/1000;wn+=2
 while wn<8 or warm<warm_ms:
  count=max(8-wn,min(128,max(1,round((warm_ms-warm)/max(.001,warm/max(1,wn))))));v=jobs[0].batch(count);warm+=v[0]/1000;wn+=count
 samples=[]
 for req in range(requests):
  j=jobs[req%d.ring];v=j.run();samples.append(dict(request=req,input_slot=j.slot,workspace_generation=req+1,gpu_us=v[0],cpu_ready_us=v[1],P_us=v[2] if v[2]>=0 else None,R_us=v[3] if v[3]>=0 else None))
 # Numerical checking and disk writes strictly outside the request interval.
 end=time.time_ns();num=d.numerical((requests-1)%d.ring,kw.get('alpha',1),kw.get('beta',0));raw_bits=None
 if check_bits is not None:
  raw_bits=bool(torch.equal(d.d.cpu().view(torch.int32),check_bits[(requests-1)%d.ring]));assert raw_bits,'PLACEMENT_RAW_BITS'
 nr=batch_replays or requests;v=jobs[0].batch(nr);num_batch=d.numerical(0,kw.get('alpha',1),kw.get('beta',0))
 row=dict(**identity,shape=[d.m,d.n,d.k],input_seed=d.seed,S=kw.get('s'),recipe=kw.get('recipe',0),actual_split_count=None if kw.get('kind')==3 else kw.get('s'),layout='TILE_SLAB' if kw.get('slab') else 'PLANAR',config=jobs[0].cfg,workspace_address=None if d.w is None else d.w.data_ptr()+kw.get('wslot',0)*d.wsize*4,workspace_capacity_bytes=0 if d.w is None else d.w.numel()*4,input_ring=d.ring,requests=requests,warmup_replays=wn,warmup_gpu_ms=warm,cpu_ready_us=float(np.mean([x['cpu_ready_us'] for x in samples])),gpu_us=float(np.mean([x['gpu_us'] for x in samples])),batch_per_replay_us=v[0]/nr,batch_replays=nr,graph_build_ms=build_ms,actual_dag=jobs[0].dag,kernel_nodes=jobs[0].nodes[0],body_nodes=jobs[0].nodes[1],runtime_state=e.state(),start_ns=start,end_ns=end,status='PASS',raw_bit_equal=raw_bits,device_uuid=UUID,build=str(BUILD),timing_scope='C++ graph submission through actual output-ready wait; GPU span and tight batch separate')
 append(out/'phases.jsonl',row);append(out/'samples.jsonl',dict(phase_id=identity['phase_id'],samples=samples));append(out/'correctness.jsonl',dict(phase_id=identity['phase_id'],final=num,batch=num_batch))
 for j in jobs:j.close()
 return row
