# 审阅使用的源码摘录
来源：用户附件 OP_FUSED_T10_REVIEW_AND_BASELINES_20261015.zip。下列为原行号摘录；本轮没有运行这些 GPU 程序。

## tools/native_bench.py:38–69
```text
38: def phase(fn,repeat,unit=1):
39:  # CUDA event spans, not GPU busy time. Only batch boundaries synchronize.
40:  def batch(n):
41:   a=torch.cuda.Event(enable_timing=True);b=torch.cuda.Event(enable_timing=True)
42:   torch.cuda.synchronize();t=time.perf_counter();a.record()
43:   for _ in range(n):fn()
44:   b.record();b.synchronize();ready=time.perf_counter()-t
45:   return a.elapsed_time(b),ready*1000
46:  warm=0;warmms=0.;start=utc()
47:  while warm<64 or warmms<300:
48:   n=max(1,math.ceil(64/unit));d,_=batch(n);warm+=n*unit;warmms+=d
49:  n=math.ceil(repeat/unit);dev,ready=batch(n)
50:  return dict(start=start,end=utc(),warmup_repeats=warm,warmup_device_ms=warmms,measured_requests=n*unit,graph_replays=n if unit>1 else None,device_interval_ms=dev/(n*unit),operator_or_layer_ready_ms=ready/(n*unit),aggregate_device_ms=dev,timing_label='CUDA_EVENT_SPAN_NOT_BUSY_TIME',p99=None)
51: 
52: def grouped(case,block):
53:  suite=case['suite']
54:  if suite=='dense_control':ms=[case['m']];ks=[case['k']];ns=[case['n']]
55:  elif suite=='heterogeneous_k':ks=case['k_per_problem'];ms=[case['m']]*len(ks);ns=[case['n']]*len(ks)
56:  else:ms=case['rows_per_expert'];ks=[case['k']]*len(ms);ns=[case['n']]*len(ms)
57:  need=sum((m*k+k*n+m*n)*2 for m,k,n in zip(ms,ks,ns))+512*2**20
58:  memory_guard(need)
59:  aa=[torch.randn(m,k,device='cuda',dtype=torch.float16)/math.sqrt(k) for m,k in zip(ms,ks)]
60:  bb=[torch.randn(k,n,device='cuda',dtype=torch.float16) for k,n in zip(ks,ns)]
61:  cc=[torch.empty(m,n,device='cuda',dtype=torch.float16) for m,n in zip(ms,ns)]
62:  def call():
63:   for a,b,c in zip(aa,bb,cc):
64:    if a.shape[0]:torch.mm(a,b,out=c)
65:   return cc
66:  call();refs=[mm_reference(a,b) if a.shape[0] else c.double() for a,b,c in zip(aa,bb,cc)]
67:  def validate():return [check(c,ref) for c,ref in zip(cc,refs) if c.numel()]
68:  ledger=dict(backend='torch.mm / cuBLAS or cuBLASLt',scope='OP_RESIDENT',gemm_api_calls=sum(m>0 for m in ms),H2D_bytes=0,D2H_bytes=0,metadata_bytes=0,extra_plan_launches=0,host_waits_inside=0,kernel_nodes=None,kernel_count_evidence='GEMM_API_CALLS_ONLY; library internal nodes require profile',weights_bytes=sum(k*n*2 for k,n in zip(ks,ns)),effective_flops=sum(2*m*k*n for m,k,n in zip(ms,ks,ns)),logical_tensor_bytes=sum(2*(m*k+k*n+m*n) for m,k,n in zip(ms,ks,ns)),source='HOST_WRAPPER')
69:  return call,validate,ledger,{'outputs':cc,'refs':refs,'inputs':aa,'weights':bb}
```

## tools/native_bench.py:71–113
```text
71: def layer(case,block):
72:  t,h,i,e,top=[case[k] for k in ('tokens','hidden','intermediate','experts','top_k')]
73:  memory_guard(3*e*h*i*2+2*2**30)
74:  # Frozen externally supplied post-route pairs. No claim to current router evaluation.
75:  gen=torch.Generator().manual_seed(2026101517+block%3+t)
76:  expert=torch.stack([torch.randperm(e,generator=gen)[:top] for _ in range(t)]).reshape(-1)
77:  order=torch.argsort(expert,stable=True);inverse=torch.argsort(order)
78:  counts=torch.bincount(expert,minlength=e).tolist();offset=[0]
79:  for m in counts:offset.append(offset[-1]+m)
80:  token=torch.arange(t).repeat_interleave(top)[order].to('cuda');inv=inverse.to('cuda')
81:  gates=torch.rand(t,top,generator=gen);gates=(gates/gates.sum(-1,keepdim=True)).to('cuda',dtype=torch.float16)
82:  x=torch.randn(t,h,device='cuda',dtype=torch.float16)
83:  wgu=torch.randn(e,h,2*i,device='cuda',dtype=torch.float16)/math.sqrt(h)
84:  wd=torch.randn(e,i,h,device='cuda',dtype=torch.float16)/math.sqrt(i)
85:  pack=torch.empty(t*top,h,device='cuda',dtype=torch.float16);gu=torch.empty(t*top,2*i,device='cuda',dtype=torch.float16)
86:  silu=torch.empty(t*top,i,device='cuda',dtype=torch.float16);act=torch.empty_like(silu)
87:  down=torch.empty(t*top,h,device='cuda',dtype=torch.float16);unpack=torch.empty_like(down)
88:  weighted=torch.empty(t,top,h,device='cuda',dtype=torch.float16);output=torch.empty(t,h,device='cuda',dtype=torch.float16)
89:  def call():
90:   torch.index_select(x,0,token,out=pack)
91:   for j in range(e):
92:    l,r=offset[j:j+2]
93:    if l<r:torch.mm(pack[l:r],wgu[j],out=gu[l:r])
94:   torch.ops.aten.silu.out(gu[:,:i],out=silu);torch.mul(silu,gu[:,i:],out=act)
95:   for j in range(e):
96:    l,r=offset[j:j+2]
97:    if l<r:torch.mm(act[l:r],wd[j],out=down[l:r])
98:   torch.index_select(down,0,inv,out=unpack);torch.mul(unpack.view(t,top,h),gates[:,:,None],out=weighted)
99:   torch.sum(weighted,dim=1,out=output)
100:   return output
101:  call();refgu=torch.empty_like(gu,dtype=torch.float64);refdown=torch.empty_like(down,dtype=torch.float64)
102:  for j in range(e):
103:   l,r=offset[j:j+2]
104:   if l<r:refgu[l:r]=mm_reference(pack[l:r],wgu[j]).half().double()
105:  # Match the native composed layer's explicit FP16 materialization boundaries.
106:  refact=(F.silu(refgu[:,:i]).half().double()*refgu[:,i:]).half()
107:  for j in range(e):
108:   l,r=offset[j:j+2]
109:   if l<r:refdown[l:r]=mm_reference(refact[l:r],wd[j]).half().double()
110:  ref=(refdown[inv].view(t,top,h)*gates.double()[:,:,None]).half().double().sum(1).half().double()
111:  def validate():return [check(output,ref)]
112:  ledger=dict(backend='AVAILABLE_COMPOSED_CUBLAS_LAYER_NOT_OPTIMIZED_MOE_LIBRARY',scope='LAYER_POST_ROUTE_REPLAY_FIXED_COUNTS',gemm_api_calls=2*sum(m>0 for m in counts),pointwise_pack_combine_api_calls=6,H2D_bytes=0,D2H_bytes=0,metadata_bytes=token.numel()*8+inv.numel()*8+gates.numel()*2,extra_plan_launches=0,host_waits_inside=0,router_included=False,count_scan_included=False,route_counts=counts,route_identity_sha256=hashlib.sha256(torch.cat((expert,order,inverse)).numpy().tobytes()).hexdigest(),route_pairs=t*top,all_expert_weights_resident=True,weights_bytes=3*e*h*i*2,effective_flops=6*t*top*h*i,kernel_nodes=None,kernel_count_evidence='HOST_WRAPPER; library internals unknown',source='HOST_WRAPPER')
113:  return call,validate,ledger,{'output':output,'ref':ref}
```

## tools/native_bench.py:140–172
```text
140:  if q==1:
141:   cq=torch.arange(b+1,device='cuda',dtype=torch.int32)*ratio
142:   ck=torch.tensor(offsets,device='cuda',dtype=torch.int32)
143:   qp=qs[:,:,0].reshape(b,hk,ratio,d).permute(0,2,1,3).contiguous().reshape(1,b*ratio,hk,d)
144:   def native(qp=qp,ck=ck):return torch.ops.aten._efficient_attention_forward(qp,kk,vv,None,cq,ck,ratio,max(lengths),0.,0)[0]
145:   def ready():
146:    pack=qs[:,:,0].reshape(b,hk,ratio,d).permute(0,2,1,3).contiguous().reshape(1,b*ratio,hk,d)
147:    return torch.ops.aten._efficient_attention_forward(pack,kk,vv,None,cq,ck,ratio,max(lengths),0.,0)[0].reshape(b,ratio,hk,d).permute(0,2,1,3).reshape(b,hq,1,d)
148:   methods['CUTLASS_RESIDENT']=(native,1,'OP_RESIDENT_PACKED_Q')
149:   methods['CUTLASS_READY']=(ready,1,'LAYOUT_PRODUCER_CONSUMER')
150:   # Input sequence is frozen before timing. Current prefixes are computed on GPU.
151:   # Three independent useful KV inputs expose cache sensitivity without cache flushing.
152:   qring=[torch.randn_like(qs) for _ in range(16)]
153:   kring=[kk,torch.randn_like(kk),torch.randn_like(kk)]
154:   vring=[vv,torch.randn_like(vv),torch.randn_like(vv)]
155:   lenring=[torch.tensor(lengths,device='cuda',dtype=torch.int32).roll(j) for j in range(16)]
156:   def dynamic():
157:    result=[]
158:    for j in range(16):
159:     prefix=torch.cat((torch.zeros(1,device='cuda',dtype=torch.int32),lenring[j].cumsum(0,dtype=torch.int32)))
160:     pack=qring[j][:,:,0].reshape(b,hk,ratio,d).permute(0,2,1,3).contiguous().reshape(1,b*ratio,hk,d)
161:     result.append(torch.ops.aten._efficient_attention_forward(pack,kring[j%3],vring[j%3],None,cq,prefix,ratio,max(lengths),0.,0)[0].reshape(b,ratio,hk,d).permute(0,2,1,3).reshape(b,hq,1,d))
162:    return result
163:   methods['CUTLASS_DYNAMIC16']=(dynamic,16,'GPU_PREFIX_AND_LAYOUT_FROZEN_INPUT_RING')
164:   drefs={}
165:   for j in [0,7,15]:
166:    lens=lengths[-j%b:]+lengths[:-j%b] if j%b else lengths[:]
167:    off=0;rr=[]
168:    for n,l in enumerate(lens):
169:     k=kring[j%3][0,off:off+l].permute(1,0,2).unsqueeze(0).double().repeat_interleave(ratio,1)
170:     v=vring[j%3][0,off:off+l].permute(1,0,2).unsqueeze(0).double().repeat_interleave(ratio,1)
171:     rr.append(torch.softmax(qring[j][n:n+1].double()@k.transpose(-1,-2)/math.sqrt(d),-1)@v);off+=l
172:    drefs[j]=torch.cat(rr)
```

## tools/grouped_library.py:18–53
```text
18: class Grouped:
19:  def __init__(self,aa,bb,cc):
20:   triples=[(a,b,c) for a,b,c in zip(aa,bb,cc) if a.shape[0]]
21:   assert triples
22:   for a,b,c in triples:
23:    assert a.is_contiguous() and b.is_contiguous() and c.is_contiguous()
24:    assert a.dtype==b.dtype==c.dtype==torch.float16
25:    assert a.shape[1]==b.shape[0] and c.shape==(a.shape[0],b.shape[1])
26:   # Standard API grouping: equal dimensions share group_size>1. Keep pointer
27:   # identity with each problem; stable first-appearance groups, no timing tuning.
28:   groups={}
29:   for a,b,c in triples:groups.setdefault((a.shape[0],b.shape[1],a.shape[1]),[]).append((a,b,c))
30:   batches=list(groups.values());triples=[triple for batch in batches for triple in batch]
31:   representatives=[batch[0] for batch in batches]
32:   self.triples=triples;self.e=len(batches);self.problem_count=len(triples)
33:   def ints(xs):return (C.c_int*self.e)(*xs)
34:   # Row-major C=A@B is column-major C^T=B^T@A^T.
35:   self.trans=ints([0]*self.e);self.m=ints([b.shape[1] for a,b,c in representatives])
36:   self.n=ints([a.shape[0] for a,b,c in representatives]);self.k=ints([a.shape[1] for a,b,c in representatives])
37:   self.sizes=ints([len(batch) for batch in batches])
38:   self.alpha=(C.c_float*self.e)(*[1.]*self.e);self.beta=(C.c_float*self.e)(*[0.]*self.e)
39:   self.ap=torch.tensor([b.data_ptr() for a,b,c in triples],device='cuda',dtype=torch.int64)
40:   self.bp=torch.tensor([a.data_ptr() for a,b,c in triples],device='cuda',dtype=torch.int64)
41:   self.cp=torch.tensor([c.data_ptr() for a,b,c in triples],device='cuda',dtype=torch.int64)
42: 
43:  def __call__(self):
44:   handle=C.c_void_p(torch.cuda.current_blas_handle())
45:   oldmath=C.c_int();oldpointer=C.c_int()
46:   ok(lib.cublasGetMathMode(handle,C.byref(oldmath)))
47:   ok(lib.cublasGetPointerMode_v2(handle,C.byref(oldpointer)))
48:   try:
49:    ok(lib.cublasSetMathMode(handle,16)) # DEFAULT | DISALLOW_REDUCED_PRECISION_REDUCTION
50:    ok(lib.cublasSetPointerMode_v2(handle,0)) # alpha/beta are host arrays
51:    ok(gemm(handle,self.trans,self.trans,self.m,self.n,self.k,self.alpha,C.c_void_p(self.ap.data_ptr()),2,self.m,C.c_void_p(self.bp.data_ptr()),2,self.k,self.beta,C.c_void_p(self.cp.data_ptr()),2,self.m,self.e,self.sizes,68))
52:   finally:
53:    ok(lib.cublasSetMathMode(handle,oldmath.value));ok(lib.cublasSetPointerMode_v2(handle,oldpointer.value))
```

## tools/strong_bench.py:27–46
```text
27: def case_run(case,block,request):
28:  torch.manual_seed(2026101517+block%3);torch.cuda.reset_peak_memory_stats();start=time.perf_counter()
29:  if request:ordinary,native,validate,ledger,storage=make_layer(case,block)
30:  else:
31:   ordinary,validate,ledger,storage=grouped(case,block)
32:   native=Grouped(storage['inputs'],storage['weights'],storage['outputs'])
33:  ordinary();assert all(x['pass'] for x in validate())
34:  native();torch.cuda.synchronize();qualification=validate();assert all(x['pass'] for x in qualification),qualification
35:  oldgraph,oldnodes=capture_readable(ordinary);newgraph,newnodes=capture_readable(native)
36:  # Both paths replay into the identical output buffers checked by the same FP64 reference.
37:  for graph in [oldgraph,newgraph]:
38:   graph.replay();torch.cuda.synchronize();assert all(x['pass'] for x in validate())
39:  calls={'PER_EXPERT_GRAPH':oldgraph.replay,'NATIVE_GROUPED_GRAPH':newgraph.replay}
40:  order=balanced_orders(list(calls),6,2026101517)[block]
41:  rows=[]
42:  for name,role in [('PER_EXPERT_GRAPH','anchor_head')]+[(n,'primary') for n in order]+[('PER_EXPERT_GRAPH','anchor_tail')]:
43:   measured=measure(calls[name]) if request else phase(calls[name],128)
44:   checks=validate();assert all(x['pass'] for x in checks),checks
45:   rows.append(dict(variant=name,phase_role=role,correctness=checks,status='COMPLETED',**measured))
46:  return dict(case=case,block=block,status='STRONG_LIBRARY_BASELINE_ONLY',candidate_status='NOT_IMPLEMENTED',phases=rows,ledger=ledger,native_grouped_ledger=dict(gemm_api_calls=2 if request else 1,metadata_scope='HOST_STATIC_DESCRIPTORS_DEVICE_POINTER_ARRAYS; setup outside timed hot replay',descriptor_rebuild_timed=False,new_scheduler=False,library=LIBRARY),graph_structure={'PER_EXPERT_GRAPH':oldnodes,'NATIVE_GROUPED_GRAPH':newnodes},scope='POST_ROUTE_FIXED_COUNTS_TRUE_REQUEST_READY' if request else 'OP_RESIDENT_AMORTIZED',qualification=qualification,elapsed_s=time.perf_counter()-start,peak_reserved_bytes=torch.cuda.max_memory_reserved(),free_bytes_after=torch.cuda.mem_get_info()[0])
```

## tools/probe_backends.py:9–23
```text
9: @triton.jit
10: def local_mm_probe(A,B,C,M:tl.constexpr,N:tl.constexpr,K:tl.constexpr,BM:tl.constexpr,BN:tl.constexpr,BK:tl.constexpr):
11:     # Literal specialization of installed torch/_inductor/kernel/mm.py's mainloop.
12:     pid=tl.program_id(0);grid_m=tl.cdiv(M,BM);grid_n=tl.cdiv(N,BN)
13:     width=8*grid_n;group_id=pid//width;group_size=tl.minimum(grid_m-group_id*8,8)
14:     pm=group_id*8+pid%group_size;pn=(pid%width)//group_size
15:     rm=pm*BM+tl.arange(0,BM);rn=pn*BN+tl.arange(0,BN);rk=tl.arange(0,BK)
16:     am=rm%M;bn=rn%N
17:     acc=tl.zeros((BM,BN),tl.float32)
18:     for ki in range(0,tl.cdiv(K,BK)):
19:         ak=rk+ki*BK
20:         a=tl.load(A+am[:,None]*K+ak[None,:],ak[None,:]<K,0)
21:         b=tl.load(B+ak[:,None]*N+bn[None,:],ak[:,None]<K,0)
22:         acc=tl.dot(a,b,acc,allow_tf32=False,out_dtype=tl.float32)
23:     tl.store(C+rm[:,None]*N+rn[None,:],acc,(rm[:,None]<M)&(rn[None,:]<N))
```

## tools/worker.py:14–45
```text
14:     rid=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+uuid.uuid4().hex[:8]
15:     out=ROOT/'runs'/rid;out.mkdir()
16:     m=dict(run_id=rid,key=key,stage=stage,status='REQUESTED',requested_at=utc(),platform='t10',
17:            campaign='OPERATOR_FUSED_SCHEDULING_DUAL_20261015',source_sha256=sha(script),
18:            protocol_sha256=sha(ROOT/'protocol/configs/campaign.json'),path=str(out.relative_to(ROOT)))
19:     command=[sys.executable,str(script),*map(str,args),'--out',str(out)]
20:     m['command']=command
21:     def save(): (out/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2))
22:     save()
23:     with open(PARENT/'environment/gpu_worker.lock','a') as lock:
24:         fcntl.flock(lock,fcntl.LOCK_EX)
25:         m['lock_acquired_at']=utc();start=time.monotonic()
26:         rows=[json.loads(x) for x in registry.read_text().splitlines()] if registry.exists() else []
27:         used=sum(x['worker_occupied_s'] for x in rows)
28:         stageused=sum(x['worker_occupied_s'] for x in rows if x['stage']==stage)
29:         if used>=57600 or stageused>=CAPS[stage]: raise RuntimeError('Worker budget exhausted')
30:         if any(p.exists() for p in [PARENT/'environment/GPU_HEALTH_STOP', ROOT/'registry/GPU_HEALTH_STOP']): raise RuntimeError('GPU health stop')
31:         if shutil.disk_usage(ROOT).free<2*2**30: raise RuntimeError('Disk reserve exhausted')
32:         query=['nvidia-smi','--query-gpu=uuid,name,driver_version,memory.total,memory.free,temperature.gpu,power.limit,ecc.errors.uncorrected.volatile.total','--format=csv']
33:         before=subprocess.check_output(query,text=True);(out/'device_before.csv').write_text(before)
34:         env=os.environ.copy();env.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_DATASETS_OFFLINE='1',TOKENIZERS_PARALLELISM='false',OMP_NUM_THREADS='2',MKL_NUM_THREADS='2',MAX_JOBS='2',TORCHINDUCTOR_COMPILE_THREADS='2',TRITON_CACHE_DIR=str(ROOT/'build/t10/triton_cache'),OP_FUSED_REMAINING_S=str(min(57600-used,CAPS[stage]-stageused)))
35:         source_bytes=pathlib.Path(script).read_bytes()
36:         m['requested_source_sha256']=m['source_sha256']
37:         m['source_sha256']=hashlib.sha256(source_bytes).hexdigest()
38:         (out/'source_snapshot.py').write_bytes(source_bytes)
39:         with open(out/'telemetry.csv','w') as telemetry,open(out/'stdout.log','w') as stdout,open(out/'stderr.log','w') as stderr:
40:             mon=subprocess.Popen(['nvidia-smi','--query-gpu=timestamp,uuid,temperature.gpu,clocks.sm,power.draw,memory.used,utilization.gpu,clocks_event_reasons.active,power.limit,enforced.power.limit','--format=csv','-l','1'],stdout=telemetry,stderr=telemetry)
41:             m['process_started_at']=utc();m['status']='RUNNING';p=subprocess.Popen(command,stdout=stdout,stderr=stderr,env=env)
42:             m['pid']=p.pid;save();rc=p.wait();m['process_ended_at']=utc();mon.terminate();mon.wait()
43:         m.update(returncode=rc,status='COMPLETED' if rc==0 else 'FAILED',worker_occupied_s=time.monotonic()-start)
44:         errors=(out/'stderr.log').read_text()
45:         if any(t in errors for t in ['illegal memory access','device-side assert','device lost','CUDA_ERROR_UNKNOWN','unspecified launch failure']):
```
