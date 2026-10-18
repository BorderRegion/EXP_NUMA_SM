"""Available native baselines. No FULL/CORE policy is implemented by this file."""
import argparse,gc,json,math,os,pathlib,sys,time,traceback,hashlib
import torch
import torch.nn.functional as F
from torch.nn.attention import sdpa_kernel,SDPBackend
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'protocol/tools'))
from reference import balanced_orders
torch.set_num_threads(2)
torch.backends.cuda.matmul.allow_tf32=False
torch.backends.cuda.matmul.allow_fp16_reduced_precision_reduction=False

def utc():
 import datetime
 return datetime.datetime.now(datetime.timezone.utc).isoformat()
def write(p,x):p.write_text(json.dumps(x,indent=2))
def check(y,ref):
 d=y.double()-ref;ab=d.abs();r=dict(max_abs=float(ab.max()),rms=float((d*d).mean().sqrt()),relative_frobenius=float(d.norm()/ref.norm().clamp_min(1e-30)),element_pass=bool((ab<=.005+.005*ref.abs()).all()))
 r['pass']=r['element_pass'] and r['relative_frobenius']<=.002
 return r
def mm_reference(a,b):
 # FP64 reference is chunked in output columns to bound converted weight memory.
 out=torch.empty((a.shape[0],b.shape[1]),device='cuda',dtype=torch.float64)
 aa=a.double()
 for j in range(0,b.shape[1],256):out[:,j:j+256]=aa@b[:,j:j+256].double()
 return out
def memory_guard(need):
 free,total=torch.cuda.mem_get_info();reserve=max(2*2**30,math.ceil(.15*total))
 if free-need<reserve:raise MemoryError(f'Need {need} new bytes; free {free}; reserve {reserve}')
def capture(fn):
 s=torch.cuda.Stream();s.wait_stream(torch.cuda.current_stream())
 with torch.cuda.stream(s):
  for _ in range(3):fn()
 s.synchronize();g=torch.cuda.CUDAGraph()
 with torch.cuda.graph(g,stream=s):y=fn()
 torch.cuda.current_stream().wait_stream(s)
 return g,y
def phase(fn,repeat,unit=1):
 # CUDA event spans, not GPU busy time. Only batch boundaries synchronize.
 def batch(n):
  a=torch.cuda.Event(enable_timing=True);b=torch.cuda.Event(enable_timing=True)
  torch.cuda.synchronize();t=time.perf_counter();a.record()
  for _ in range(n):fn()
  b.record();b.synchronize();ready=time.perf_counter()-t
  return a.elapsed_time(b),ready*1000
 warm=0;warmms=0.;start=utc()
 while warm<64 or warmms<300:
  n=max(1,math.ceil(64/unit));d,_=batch(n);warm+=n*unit;warmms+=d
 n=math.ceil(repeat/unit);dev,ready=batch(n)
 return dict(start=start,end=utc(),warmup_repeats=warm,warmup_device_ms=warmms,measured_requests=n*unit,graph_replays=n if unit>1 else None,device_interval_ms=dev/(n*unit),operator_or_layer_ready_ms=ready/(n*unit),aggregate_device_ms=dev,timing_label='CUDA_EVENT_SPAN_NOT_BUSY_TIME',p99=None)

def grouped(case,block):
 suite=case['suite']
 if suite=='dense_control':ms=[case['m']];ks=[case['k']];ns=[case['n']]
 elif suite=='heterogeneous_k':ks=case['k_per_problem'];ms=[case['m']]*len(ks);ns=[case['n']]*len(ks)
 else:ms=case['rows_per_expert'];ks=[case['k']]*len(ms);ns=[case['n']]*len(ms)
 need=sum((m*k+k*n+m*n)*2 for m,k,n in zip(ms,ks,ns))+512*2**20
 memory_guard(need)
 aa=[torch.randn(m,k,device='cuda',dtype=torch.float16)/math.sqrt(k) for m,k in zip(ms,ks)]
 bb=[torch.randn(k,n,device='cuda',dtype=torch.float16) for k,n in zip(ks,ns)]
 cc=[torch.empty(m,n,device='cuda',dtype=torch.float16) for m,n in zip(ms,ns)]
 def call():
  for a,b,c in zip(aa,bb,cc):
   if a.shape[0]:torch.mm(a,b,out=c)
  return cc
 call();refs=[mm_reference(a,b) if a.shape[0] else c.double() for a,b,c in zip(aa,bb,cc)]
 def validate():return [check(c,ref) for c,ref in zip(cc,refs) if c.numel()]
 ledger=dict(backend='torch.mm / cuBLAS or cuBLASLt',scope='OP_RESIDENT',gemm_api_calls=sum(m>0 for m in ms),H2D_bytes=0,D2H_bytes=0,metadata_bytes=0,extra_plan_launches=0,host_waits_inside=0,kernel_nodes=None,kernel_count_evidence='GEMM_API_CALLS_ONLY; library internal nodes require profile',weights_bytes=sum(k*n*2 for k,n in zip(ks,ns)),effective_flops=sum(2*m*k*n for m,k,n in zip(ms,ks,ns)),logical_tensor_bytes=sum(2*(m*k+k*n+m*n) for m,k,n in zip(ms,ks,ns)),source='HOST_WRAPPER')
 return call,validate,ledger,{'outputs':cc,'refs':refs,'inputs':aa,'weights':bb}

def layer(case,block):
 t,h,i,e,top=[case[k] for k in ('tokens','hidden','intermediate','experts','top_k')]
 memory_guard(3*e*h*i*2+2*2**30)
 # Frozen externally supplied post-route pairs. No claim to current router evaluation.
 gen=torch.Generator().manual_seed(2026101517+block%3+t)
 expert=torch.stack([torch.randperm(e,generator=gen)[:top] for _ in range(t)]).reshape(-1)
 order=torch.argsort(expert,stable=True);inverse=torch.argsort(order)
 counts=torch.bincount(expert,minlength=e).tolist();offset=[0]
 for m in counts:offset.append(offset[-1]+m)
 token=torch.arange(t).repeat_interleave(top)[order].to('cuda');inv=inverse.to('cuda')
 gates=torch.rand(t,top,generator=gen);gates=(gates/gates.sum(-1,keepdim=True)).to('cuda',dtype=torch.float16)
 x=torch.randn(t,h,device='cuda',dtype=torch.float16)
 wgu=torch.randn(e,h,2*i,device='cuda',dtype=torch.float16)/math.sqrt(h)
 wd=torch.randn(e,i,h,device='cuda',dtype=torch.float16)/math.sqrt(i)
 pack=torch.empty(t*top,h,device='cuda',dtype=torch.float16);gu=torch.empty(t*top,2*i,device='cuda',dtype=torch.float16)
 silu=torch.empty(t*top,i,device='cuda',dtype=torch.float16);act=torch.empty_like(silu)
 down=torch.empty(t*top,h,device='cuda',dtype=torch.float16);unpack=torch.empty_like(down)
 weighted=torch.empty(t,top,h,device='cuda',dtype=torch.float16);output=torch.empty(t,h,device='cuda',dtype=torch.float16)
 def call():
  torch.index_select(x,0,token,out=pack)
  for j in range(e):
   l,r=offset[j:j+2]
   if l<r:torch.mm(pack[l:r],wgu[j],out=gu[l:r])
  torch.ops.aten.silu.out(gu[:,:i],out=silu);torch.mul(silu,gu[:,i:],out=act)
  for j in range(e):
   l,r=offset[j:j+2]
   if l<r:torch.mm(act[l:r],wd[j],out=down[l:r])
  torch.index_select(down,0,inv,out=unpack);torch.mul(unpack.view(t,top,h),gates[:,:,None],out=weighted)
  torch.sum(weighted,dim=1,out=output)
  return output
 call();refgu=torch.empty_like(gu,dtype=torch.float64);refdown=torch.empty_like(down,dtype=torch.float64)
 for j in range(e):
  l,r=offset[j:j+2]
  if l<r:refgu[l:r]=mm_reference(pack[l:r],wgu[j]).half().double()
 # Match the native composed layer's explicit FP16 materialization boundaries.
 refact=(F.silu(refgu[:,:i]).half().double()*refgu[:,i:]).half()
 for j in range(e):
  l,r=offset[j:j+2]
  if l<r:refdown[l:r]=mm_reference(refact[l:r],wd[j]).half().double()
 ref=(refdown[inv].view(t,top,h)*gates.double()[:,:,None]).half().double().sum(1).half().double()
 def validate():return [check(output,ref)]
 ledger=dict(backend='AVAILABLE_COMPOSED_CUBLAS_LAYER_NOT_OPTIMIZED_MOE_LIBRARY',scope='LAYER_POST_ROUTE_REPLAY_FIXED_COUNTS',gemm_api_calls=2*sum(m>0 for m in counts),pointwise_pack_combine_api_calls=6,H2D_bytes=0,D2H_bytes=0,metadata_bytes=token.numel()*8+inv.numel()*8+gates.numel()*2,extra_plan_launches=0,host_waits_inside=0,router_included=False,count_scan_included=False,route_counts=counts,route_identity_sha256=hashlib.sha256(torch.cat((expert,order,inverse)).numpy().tobytes()).hexdigest(),route_pairs=t*top,all_expert_weights_resident=True,weights_bytes=3*e*h*i*2,effective_flops=6*t*top*h*i,kernel_nodes=None,kernel_count_evidence='HOST_WRAPPER; library internals unknown',source='HOST_WRAPPER')
 return call,validate,ledger,{'output':output,'ref':ref}

def attention(case,block):
 b=case['batch'];hq=case['q_heads'];hk=case['kv_heads'];d=case['head_dim'];q=case['query_length']
 lengths=case.get('lengths',[case['kv_length']]*b) if 'lengths' not in case else case['lengths']
 total=sum(lengths);ratio=hq//hk
 # Include FP64 reference and math backend's temporary softmax score storage.
 need=total*hk*d*2*8 + b*hq*q*max(lengths)*12 + 512*2**20
 memory_guard(need)
 qs=torch.randn(b,hq,q,d,device='cuda',dtype=torch.float16)
 kk=torch.randn(1,total,hk,d,device='cuda',dtype=torch.float16);vv=torch.randn_like(kk)
 offsets=[0]
 for l in lengths:offsets.append(offsets[-1]+l)
 keys=[kk[0,offsets[j]:offsets[j+1]].permute(1,0,2).unsqueeze(0) for j in range(b)]
 vals=[vv[0,offsets[j]:offsets[j+1]].permute(1,0,2).unsqueeze(0) for j in range(b)]
 def math_call():
  with sdpa_kernel(SDPBackend.MATH):return [F.scaled_dot_product_attention(qs[j:j+1],keys[j],vals[j],enable_gqa=True) for j in range(b)]
 refs=[]
 for j in range(b):
  kr=keys[j].double().repeat_interleave(ratio,1);vr=vals[j].double().repeat_interleave(ratio,1)
  blocks=[]
  for l in range(0,q,32):blocks.append(torch.softmax(qs[j:j+1,:,l:l+32].double()@kr.transpose(-1,-2)/math.sqrt(d),-1)@vr)
  refs.append(torch.cat(blocks,2))
 ref=torch.cat(refs)
 methods={'MATH_READY':(math_call,1,'OP_RESIDENT_NATIVE_MATH_GQA')}
 ledger=dict(backend='PyTorch native attention',scope='OP_RESIDENT_AND_LAYOUT_READY',H2D_bytes=0,D2H_bytes=0,metadata_bytes=4*(2*b+2),extra_plan_launches=0,host_waits_inside=0,mask='NON_CAUSAL_FULL_KV',query_heads=hq,kv_heads=hk,lengths=lengths,actual_gqa_sharing=True,effective_flops=4*hq*q*total*d,kv_bytes=4*total*hk*d,source='HOST_WRAPPER',kernel_nodes=None)
 storage={'refs':refs,'ref':ref,'qs':qs,'kk':kk,'vv':vv}
 if q==1:
  cq=torch.arange(b+1,device='cuda',dtype=torch.int32)*ratio
  ck=torch.tensor(offsets,device='cuda',dtype=torch.int32)
  qp=qs[:,:,0].reshape(b,hk,ratio,d).permute(0,2,1,3).contiguous().reshape(1,b*ratio,hk,d)
  def native(qp=qp,ck=ck):return torch.ops.aten._efficient_attention_forward(qp,kk,vv,None,cq,ck,ratio,max(lengths),0.,0)[0]
  def ready():
   pack=qs[:,:,0].reshape(b,hk,ratio,d).permute(0,2,1,3).contiguous().reshape(1,b*ratio,hk,d)
   return torch.ops.aten._efficient_attention_forward(pack,kk,vv,None,cq,ck,ratio,max(lengths),0.,0)[0].reshape(b,ratio,hk,d).permute(0,2,1,3).reshape(b,hq,1,d)
  methods['CUTLASS_RESIDENT']=(native,1,'OP_RESIDENT_PACKED_Q')
  methods['CUTLASS_READY']=(ready,1,'LAYOUT_PRODUCER_CONSUMER')
  # Input sequence is frozen before timing. Current prefixes are computed on GPU.
  # Three independent useful KV inputs expose cache sensitivity without cache flushing.
  qring=[torch.randn_like(qs) for _ in range(16)]
  kring=[kk,torch.randn_like(kk),torch.randn_like(kk)]
  vring=[vv,torch.randn_like(vv),torch.randn_like(vv)]
  lenring=[torch.tensor(lengths,device='cuda',dtype=torch.int32).roll(j) for j in range(16)]
  def dynamic():
   result=[]
   for j in range(16):
    prefix=torch.cat((torch.zeros(1,device='cuda',dtype=torch.int32),lenring[j].cumsum(0,dtype=torch.int32)))
    pack=qring[j][:,:,0].reshape(b,hk,ratio,d).permute(0,2,1,3).contiguous().reshape(1,b*ratio,hk,d)
    result.append(torch.ops.aten._efficient_attention_forward(pack,kring[j%3],vring[j%3],None,cq,prefix,ratio,max(lengths),0.,0)[0].reshape(b,ratio,hk,d).permute(0,2,1,3).reshape(b,hq,1,d))
   return result
  methods['CUTLASS_DYNAMIC16']=(dynamic,16,'GPU_PREFIX_AND_LAYOUT_FROZEN_INPUT_RING')
  drefs={}
  for j in [0,7,15]:
   lens=lengths[-j%b:]+lengths[:-j%b] if j%b else lengths[:]
   off=0;rr=[]
   for n,l in enumerate(lens):
    k=kring[j%3][0,off:off+l].permute(1,0,2).unsqueeze(0).double().repeat_interleave(ratio,1)
    v=vring[j%3][0,off:off+l].permute(1,0,2).unsqueeze(0).double().repeat_interleave(ratio,1)
    rr.append(torch.softmax(qring[j][n:n+1].double()@k.transpose(-1,-2)/math.sqrt(d),-1)@v);off+=l
   drefs[j]=torch.cat(rr)
  storage.update(drefs=drefs,qring=qring,lenring=lenring,kring=kring,vring=vring)
  ledger.update(gqa_layout='four query heads per KV head recast as four independent query rows; decode only',dynamic_input_ring=16,dynamic_kv_ring=3,kv_cache_condition='STEADY_HOT_VS_THREE_INDEPENDENT_SYNTHETIC_KV_INPUTS',prefix_producer='zeros+cumsum+cat each request, baseline cost included',new_scheduler=False)
 def validate(name,y):
  if name=='MATH_READY':return [check(torch.cat(y),ref)]
  if name=='CUTLASS_RESIDENT':return [check(y.reshape(b,ratio,hk,d).permute(0,2,1,3).reshape(b,hq,1,d),ref)]
  if name=='CUTLASS_DYNAMIC16':return [dict(sequence_index=j,**check(y[j],storage['drefs'][j])) for j in [0,7,15]]
  return [check(y,ref)]
 return methods,validate,ledger,storage

def run_case(case,block,stage,out,profile=False):
 start=time.perf_counter();torch.manual_seed(2026101517+block%3)
 torch.cuda.reset_peak_memory_stats();suite=case['suite'];result=dict(case=case,block=block,source_type='SYNTHETIC_MECHANISM',candidate_status='NOT_IMPLEMENTED_BACKEND_GAP',phases=[])
 if suite.startswith('attention') or suite=='prefill_control':
  methods,validate,ledger,storage=attention(case,block);entries={}
  for name,(fn,unit,scope) in methods.items():
   yy=fn();checks=validate(name,yy)
   if not all(x['pass'] for x in checks):raise ValueError('Numerical qualification failed '+name+str(checks))
   # Equal Graph batching opportunity: every decode variant has 16 requests/Graph.
   # Dynamic consumes 16 distinct Q/length items; steady variants repeat their input.
   if suite=='attention_decode' and unit==1:
    def batch_fn(fn=fn):return [fn() for _ in range(16)]
    g,yy=capture(batch_fn);unit=16
    def validate_graph(yy=yy,name=name):return [dict(graph_request=j,**c) for j in [0,7,15] for c in validate(name,yy[j])]
   else:
    g,yy=capture(fn)
    def validate_graph(yy=yy,name=name):return validate(name,yy)
   g.replay();torch.cuda.synchronize()
   if not all(x['pass'] for x in validate_graph()):raise ValueError('Captured path qualification failed '+name)
   entries[name]=(g.replay,validate_graph,unit,scope,'GRAPH',None)
  names=list(entries);anchor='CUTLASS_READY' if 'CUTLASS_READY' in entries else 'MATH_READY'
  # Frozen from the two development qualification points (B1,L128 and B16,L1024).
  # Use one replay length for every policy of this case, including the slower MATH path.
  if suite=='attention_decode':
   predicted_ms=.014+.4*sum(case['lengths'])/16384
   repeat=min(512,max(128,math.ceil((100/predicted_ms)/128)*128))
  else:repeat=128
 else:
  fn,validate,ledger,storage=(layer(case,block) if suite=='moe_layer' else grouped(case,block))
  checks=validate()
  if not all(x['pass'] for x in checks):raise ValueError('Numerical qualification failed '+str(checks))
  entries={};libs=['cublas','cublaslt'] if stage=='E1' else [json.loads((ROOT/'preregistration/library_freeze.json').read_text())['selected']]
  for lib in libs:
   torch.backends.cuda.preferred_blas_library(lib);g,yy=capture(fn)
   entries[lib.upper()+'_GRAPH']=(g.replay,validate,1,ledger['scope'],'GRAPH',lib)
  if stage!='E1':entries[libs[0].upper()+'_EAGER']=(fn,validate,1,ledger['scope'],'EAGER',libs[0])
  names=list(entries);anchor=names[0];repeat=128
  # Hold graph objects through bound replay functions in entries.
 result['ledger']=ledger;result['initialization_and_reference_s']=time.perf_counter()-start
 order=balanced_orders(names,6,2026101517)[block];phases=[(anchor,'anchor_head')]+[(n,'primary') for n in order]+[(anchor,'anchor_tail')]
 result['phase_order']=[n+':'+role for n,role in phases];result['seed']=2026101517+block%3
 if profile:
  profile_name='CUTLASS_DYNAMIC16' if 'CUTLASS_DYNAMIC16' in entries else anchor
  entry=entries[profile_name]
  with torch.profiler.profile(activities=[torch.profiler.ProfilerActivity.CPU,torch.profiler.ProfilerActivity.CUDA]) as prof:entry[0]();torch.cuda.synchronize()
  prof.export_chrome_trace(str(out/(case['case_id']+'_trace.json')))
  result['observed_cuda_kernels']=[e.name for e in prof.events() if e.device_type==torch.autograd.DeviceType.CUDA]
  result['observed_profile_variant']=profile_name;result['observed_profile_requests']=entry[2]
 for name,role in phases:
  fn,validate_one,unit,scope,mode,lib=entries[name]
  if lib:torch.backends.cuda.preferred_blas_library(lib)
  measured=phase(fn,repeat,unit);checks=validate_one()
  passed=all(x['pass'] for x in checks)
  result['phases'].append(dict(variant=name,phase_role=role,scope=scope,mode=mode,unit_requests=unit,status='COMPLETED' if passed else 'NUMERICAL_FAILED',correctness=checks,**measured))
  if not passed:raise ValueError('Post-phase numerical failure '+name+str(checks))
 result.update(status='BASELINE_ONLY',peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=torch.cuda.max_memory_reserved(),free_bytes_after=torch.cuda.mem_get_info()[0],elapsed_s=time.perf_counter()-start)
 return result

def main(args):
 write(args.out/'runtime.json',dict(python=sys.executable,torch=torch.__version__,cuda_runtime=torch.version.cuda,device=str(torch.cuda.get_device_properties(0)),allow_tf32=torch.backends.cuda.matmul.allow_tf32,allow_fp16_reduced_precision_reduction=torch.backends.cuda.matmul.allow_fp16_reduced_precision_reduction,library_freeze_sha256=hashlib.sha256((ROOT/'preregistration/library_freeze.json').read_bytes()).hexdigest() if (ROOT/'preregistration/library_freeze.json').exists() else None))
 allcases=[json.loads(x) for x in (ROOT/'preregistration/plan.jsonl').read_text().splitlines()]
 ids=json.loads((ROOT/'preregistration/selected_baselines.json').read_text())['selection'][args.stage]
 if args.only:ids=args.only.split(',')
 cases=[x for x in allcases if x['case_id'] in ids]
 deadline=time.monotonic()+float(os.environ.get('OP_FUSED_REMAINING_S','100000'))-30
 profile_cases={'E1':{'grouped-001','grouped-018'},'E4':{'moe_layer-001'},'E5':{'attention_decode-001'}}
 for c in cases:
  if time.monotonic()>deadline:
   write(args.out/(c['case_id']+'.json'),dict(case=c,status='BUDGET_SKIPPED'));continue
  try:r=run_case(c,args.block,args.stage,args.out,profile=args.block==0 and c['case_id'] in profile_cases.get(args.stage,set()))
  except (MemoryError,torch.OutOfMemoryError) as e:r=dict(case=c,block=args.block,status='MEMORY_UNSUPPORTED',error=str(e))
  except Exception as e:
   if any(s in str(e) for s in ['illegal memory access','device-side assert','unspecified launch failure']):raise
   r=dict(case=c,block=args.block,status='FAILED',error=str(e),traceback=traceback.format_exc())
  write(args.out/(c['case_id']+'.json'),r);print(c['case_id'],r['status'],round(r.get('elapsed_s',0),2),flush=True)
  gc.collect();torch.cuda.empty_cache()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--stage',required=True);p.add_argument('--block',type=int,required=True);p.add_argument('--only');p.add_argument('--out',type=pathlib.Path,required=True);main(p.parse_args())
