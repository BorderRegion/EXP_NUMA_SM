"""Native workload inventory and negative controls; no NUMA candidate labels."""
import argparse,gc,hashlib,json,math,sys,time
from pathlib import Path
import numpy as np
import torch
from common import *
from scratch_scan import ScratchScan
from graph_inspect import inspect_graph
KEEP_GRAPH=False
sys.path.insert(0,str(REPO/'op-fused/tools'))
from same_q_v2_backend import CutlassGrouped
torch.set_num_threads(2)
torch.backends.cuda.preferred_blas_library('cublas')
torch.backends.cuda.matmul.allow_tf32=False
torch.backends.cuda.matmul.allow_fp16_reduced_precision_reduction=False
GEMM=[dict(id='gemm_small',rows=[8]*4,k=2048,n=4096),dict(id='gemm_reuse',rows=[96]*4,k=2048,n=4096),dict(id='gemm_compute',rows=[512]*4,k=2048,n=4096),dict(id='gemm_skew',rows=[1,8,64,256,0,3,16,128],k=1024,n=2048)]
ATTN=[dict(id='decode_short',lengths=[128]),dict(id='decode_long',lengths=[8192]),dict(id='decode_batch',lengths=[2048]*8),dict(id='decode_skew',lengths=[33,257,1024,8192])]
def check(y,ref,fp32=False):
 d=y.double()-ref;ab=d.abs();relative=float(d.norm()/ref.norm().clamp_min(1e-30));atol,rtol,rel=(3e-4,3e-4,1e-4) if fp32 else (.005,.005,.002)
 good=bool((ab<=atol+rtol*ref.abs()).all()) and relative<=rel
 return dict(pass_=good,max_abs=float(ab.max()) if ab.numel() else 0,relative_frobenius=relative,atol=atol,rtol=rtol,relative_limit=rel)
def capture(fn):
 s=torch.cuda.Stream();s.wait_stream(torch.cuda.current_stream())
 with torch.cuda.stream(s):
  for _ in range(3):fn()
 s.synchronize();g=torch.cuda.CUDAGraph(keep_graph=KEEP_GRAPH)
 with torch.cuda.graph(g,stream=s):out=fn()
 torch.cuda.current_stream().wait_stream(s)
 if KEEP_GRAPH:g.instantiate()
 return g,out
def mm_ref(a,b):
 ref=torch.empty((a.shape[0],b.shape[1]),device='cuda',dtype=torch.float64)
 for j in range(0,b.shape[1],256):ref[:,j:j+256]=a.double()@b[:,j:j+256].double()
 return ref
def grouped(c):
 aa=[torch.randn(m,c['k'],device='cuda',dtype=torch.float16)/math.sqrt(c['k']) for m in c['rows']];bb=[torch.randn(c['k'],c['n'],device='cuda',dtype=torch.float16) for m in c['rows']];cc=[torch.empty(m,c['n'],device='cuda',dtype=torch.float16) for m in c['rows']]
 bank=[[torch.randn_like(a)/math.sqrt(c['k']) for a in aa] for _ in range(4)];refs=[[mm_ref(a,b) for a,b in zip(xs,bb)] for xs in bank]
 core=CutlassGrouped(aa,bb,cc,recipe=0,mode=0,q_cap=1);minimal=CutlassGrouped(aa,bb,cc,recipe=0,mode=3,q_cap=1)
 def lib():
  for a,b,c in zip(aa,bb,cc):
   if a.shape[0]:torch.mm(a,b,out=c)
 def call(fn,slot):
  for a,x in zip(aa,bank[slot]):a.copy_(x)
  fn();return cc
 calls={name:[lambda fn=fn,s=s:call(fn,s) for s in range(4)] for name,fn in [('N_CUBLAS',lib),('B_Q1_MINIMAL',minimal),('CORE_DIAGNOSTIC',core)]}
 def validate(y,slot):return [check(a,r) for a,r in zip(y,refs[slot]) if a.numel()]
 # Same-body order equivalence is raw bits, separately from cross-library error.
 for s in range(4):
  call(core,s);refbits=[x.view(torch.int16).clone() for x in cc];call(minimal,s)
  assert all(torch.equal(x.view(torch.int16),r) for x,r in zip(cc,refbits))
 weights=sum(x.numel()*x.element_size() for x in bb);inp=sum(x.numel()*x.element_size() for x in aa);outb=sum(x.numel()*x.element_size() for x in cc)
 card=dict(family='inference_grouped',source_type='SYNTHETIC_MECHANISM_NOT_REAL_MODEL',effective_flops=sum(2*m*c['k']*c['n'] for m in c['rows']),weights_bytes=weights,resident_weights_bytes=weights,active_weight_tensor_bytes=sum(b.numel()*b.element_size() for a,b in zip(aa,bb) if a.shape[0]),activation_bytes=inp,output_bytes=outb,unique_tensor_bytes=weights+inp+outb,tensor_bytes_scope='resident tensor footprints, not measured traffic; zero-row problem weights are allocated but not consumed; four input slots and reference tensors separately resident during research',input_producer='captured equal D2D activation copy for all implementations',weight_reuse_proxy='M rows per problem; no hardware traffic assertion',q1_metadata=minimal.metadata(),same_body_raw_bit_qualification=4,actual_home_known_fraction=0)
 return calls,validate,card,[aa,bb,cc,bank,refs,core,minimal]
def sparse(c):
 path=REPO/'assets/prepared'/c['matrix']/'csr.bin'
 with path.open('rb') as f:
  n,nz=np.fromfile(f,'<u4',2).astype(int);row=np.fromfile(f,'<i4',n+1);col=np.fromfile(f,'<i4',nz)
 degree=np.diff(row);ix=np.arange(nz,dtype=np.uint64);values=(((ix*1664525+1013904223)%65521).astype(np.float64)/65521-.5).astype(np.float32)
 crow=torch.from_numpy(row.copy());ccol=torch.from_numpy(col.copy());v=torch.from_numpy(values)
 cpu=torch.sparse_csr_tensor(crow,ccol,v.double(),size=(n,n));mat=torch.sparse_csr_tensor(crow.cuda(),ccol.cuda(),v.cuda(),size=(n,n))
 bank=[torch.randn(n,c['rhs'],dtype=torch.float32) for _ in range(4)];refs=[torch.sparse.mm(cpu,x.double()).cuda() for x in bank];bank=[x.cuda() for x in bank];x=torch.empty_like(bank[0])
 def call(slot):x.copy_(bank[slot]);return torch.sparse.mm(mat,x)
 calls={'N_CUSPARSE':[lambda s=s:call(s) for s in range(4)]}
 def validate(y,slot):return [check(y,refs[slot],True)]
 chosen=np.linspace(0,n-1,min(1024,n),dtype=int);pages=[len(np.unique((x.data_ptr()+col[row[r]:row[r+1]].astype(np.int64)*c['rhs']*4)//4096)) for r in chosen]
 card=dict(family='sparse',source_type='REAL_GRAPH_STRUCTURE_GENERAL_REPRODUCIBLE_VALUES',input_sha256=sha(path),rows=int(n),nnz=int(nz),rhs=c['rhs'],values_formula='float32(((j*1664525+1013904223)%65521)/65521-0.5)',effective_flops=int(2*nz*c['rhs']),matrix_bytes=int((n+1+nz)*4+nz*4),x_bytes=int(n*c['rhs']*4),consumer_unique_indexed_x_bytes=int(np.unique(col).size*c['rhs']*4),tensor_bytes_scope='resident CSR and input/output tensor sizes, not measured DRAM bytes; captured producer copies full x even when some rows are unreferenced',output_bytes=int(n*c['rhs']*4),row_degree_quantiles=np.quantile(degree,[0,.5,.9,.99,1]).tolist(),column_reuse_quantiles=np.quantile(np.bincount(col,minlength=n),[0,.5,.9,.99,1]).tolist(),sampled_rows=len(chosen),x_virtual_page_span_quantiles=np.quantile(pages,[0,.5,.9,.99,1]).tolist(),actual_home_known_fraction=0,indices='original CSR order and int32 indices preserved; values are general, not unit weights',input_producer='same captured D2D x copy',full_application_claim=False)
 return calls,validate,card,[cpu,mat,bank,x,refs]
def attention(c):
 lengths=c['lengths'];b=len(lengths);hq,hk,d,ratio=32,8,128,4;total=sum(lengths);offset=np.cumsum([0]+lengths).tolist()
 qs=[torch.randn(b,hq,1,d,device='cuda',dtype=torch.float16) for _ in range(4)];ks=[torch.randn(1,total,hk,d,device='cuda',dtype=torch.float16) for _ in range(4)];vs=[torch.randn_like(k) for k in ks]
 cq=torch.arange(b+1,device='cuda',dtype=torch.int32)*ratio;ck=torch.tensor(offset,device='cuda',dtype=torch.int32);refs=[]
 for s in range(4):
  result=[]
  for j,l in enumerate(lengths):
   k=ks[s][0,offset[j]:offset[j+1]].permute(1,0,2).unsqueeze(0).double().repeat_interleave(ratio,1);v=vs[s][0,offset[j]:offset[j+1]].permute(1,0,2).unsqueeze(0).double().repeat_interleave(ratio,1)
   result.append(torch.softmax(qs[s][j:j+1].double()@k.transpose(-1,-2)/math.sqrt(d),-1)@v)
  refs.append(torch.cat(result))
 def call(slot):
  q=qs[slot][:,:,0].reshape(b,hk,ratio,d).permute(0,2,1,3).contiguous().reshape(1,b*ratio,hk,d)
  y=torch.ops.aten._efficient_attention_forward(q,ks[slot],vs[slot],None,cq,ck,ratio,max(lengths),0.,0)[0]
  return y.reshape(b,ratio,hk,d).permute(0,2,1,3).reshape(b,hq,1,d)
 calls={'N_CUTLASS_ATTENTION':[lambda s=s:call(s) for s in range(4)]}
 def validate(y,slot):return [check(y,refs[slot])]
 card=dict(family='inference_decode',source_type='SYNTHETIC_MECHANISM_NOT_REAL_LLM',lengths=lengths,q_heads=hq,kv_heads=hk,head_dim=d,effective_flops=4*hq*total*d,kv_bytes=4*total*hk*d,unique_tensor_bytes=4*total*hk*d+b*hq*d*4,query_producer='GQA query-head packing in Graph; output-layout view included',kv_ring='four independent resident input buffers; graph selection included in request; no claim to production append/update',mask='full noncausal KV for one query',actual_home_known_fraction=0)
 return calls,validate,card,[qs,ks,vs,cq,ck,refs]
def run_case(c,block,out,profile=False,requests=128,repeat_plan=None):
 out.mkdir(parents=True,exist_ok=False);torch.manual_seed(2026101633+block*101+int(hashlib.sha256(c['id'].encode()).hexdigest()[:6],16));start=time.perf_counter();torch.cuda.reset_peak_memory_stats()
 calls,validate,card,storage=(sparse(c) if c['id'].startswith('sparse') else attention(c) if c['id'].startswith('decode') else grouped(c))
 scratch=ScratchScan();graphs={};qual=[]
 for name,functions in calls.items():
  graphset=[]
  for slot,fn in enumerate(functions):
   g,y=capture(fn);g.replay();torch.cuda.synchronize();checks=validate(y,slot);assert all(q['pass_'] for q in checks),(c,name,checks);qual.extend(dict(method=name,slot=slot,**q) for q in checks);graphset.append((g,y))
   if profile and name.startswith('N'):
    torch.save([t.detach().cpu() for t in y] if isinstance(y,list) else y.detach().cpu(),out/f'native_slot_{slot}.pt')
  graphs[name]=graphset
 if KEEP_GRAPH:
  card['actual_graph_inventory']={name:inspect_graph(gs[0][0]) for name,gs in graphs.items()}
 if profile:
  traces={}
  for name in graphs:
   with torch.profiler.profile(activities=[torch.profiler.ProfilerActivity.CPU,torch.profiler.ProfilerActivity.CUDA]) as prof:
    graphs[name][0][0].replay();torch.cuda.synchronize()
   prof.export_chrome_trace(str(out/(name+'_trace.json')));traces[name]=[e.name for e in prof.events() if e.device_type==torch.autograd.DeviceType.CUDA]
  card['actual_graph_cuda_events']=traces
  card['trace_scope']='actual captured graph replay, outside performance timings; CUPTI traces may be incomplete (including empty), not an authoritative kernel count. Use direct retained-graph inventory when available.'
 init_s=time.perf_counter()-start;card['setup_timing_scope']='input synthesis/load, allocation, FP64 reference, raw-bit qualification, graph capture and optional diagnostic profile; research setup, not deployment-only startup';phases=[];names=list(graphs);names=names[block%len(names):]+names[:block%len(names)];states=['HOT_SLOT0','INPUT_RING4','EVICTION_CONDITIONED'];states=states[block%3:]+states[:block%3]
 for state in states:
  def batch(name,repeats):
   begin=torch.cuda.Event(enable_timing=True);end=torch.cuda.Event(enable_timing=True);torch.cuda.synchronize();start_ns=time.monotonic_ns();t=time.perf_counter();begin.record()
   for i in range(repeats):
    if state=='EVICTION_CONDITIONED':scratch()
    slot=i%4 if state=='INPUT_RING4' else 0;graphs[name][slot][0].replay()
   end.record();end.synchronize();return dict(repeats=repeats,event_span_ms=begin.elapsed_time(end),cpu_ready_ms=(time.perf_counter()-t)*1000,start_monotonic_ns=start_ns,end_monotonic_ns=time.monotonic_ns(),scope='EVICTION_PLUS_CONSUMER' if state=='EVICTION_CONDITIONED' else 'GRAPH_REQUESTS',timing='CUDA_EVENT_SPAN_INCLUDES_SUBMISSION_GAPS; not GPU busy time')
  pilot_name=next(iter(graphs))
  if repeat_plan is None:
   batch(pilot_name,64);pilot=batch(pilot_name,128);repeat=min(32768,max(64,math.ceil(100/pilot['event_span_ms'])*128))
  else:
   repeat=int(repeat_plan[c['id']][state]);pilot=dict(source='P2_NATIVE_FROZEN_BEFORE_P4',repeats=repeat);batch(pilot_name,64)
  # Head/tail N anchors bracket all controls; primary N remains in the order.
  order=[(next(iter(graphs)),'anchor_head')]+[(n,'primary') for n in names]+[(next(iter(graphs)),'anchor_tail')]
  for name,role in order:
   phase_start=utc();phase_start_ns=time.monotonic_ns()
   event0=torch.cuda.Event(enable_timing=True);event1=torch.cuda.Event(enable_timing=True)
   def once(i):
    slot=i%4 if state=='INPUT_RING4' else 0;prep=0
    if state=='EVICTION_CONDITIONED':
     t=time.perf_counter();scratch();torch.cuda.synchronize();prep=(time.perf_counter()-t)*1000
    t=time.perf_counter();event0.record();graphs[name][slot][0].replay();event1.record();event1.synchronize();ready=(time.perf_counter()-t)*1000
    return slot,event0.elapsed_time(event1),ready,prep
   warm=0;warm_ms=0
   while warm<64 or warm_ms<150:
    _,d,_,_=once(warm);warm+=1;warm_ms+=d
   measured=[];checks=[];measured_start_ns=time.monotonic_ns()
   for i in range(requests):
    slot,d,t,prep=once(i);measured.append([d,t,prep])
    if i in [0,requests//2,requests-1]:
     q=validate(graphs[name][slot][1],slot);assert all(x['pass_'] for x in q),(c,name,state,q);checks.extend(dict(request=i,slot=slot,**x) for x in q)
   throughput=batch(name,repeat);slot=(repeat-1)%4 if state=='INPUT_RING4' else 0;q=validate(graphs[name][slot][1],slot);assert all(x['pass_'] for x in q),(c,name,state,'throughput',q);checks.extend(dict(request='batch_end',slot=slot,**x) for x in q)
   phases.append(dict(method=name,role=role,state=state,start_utc=phase_start,end_utc=utc(),start_monotonic_ns=phase_start_ns,measured_start_monotonic_ns=measured_start_ns,end_monotonic_ns=time.monotonic_ns(),warmup_repeats=warm,warmup_event_ms=warm_ms,measured_requests=requests,samples_columns=['event_ms','cpu_ready_ms','cache_prepare_ms'],samples=measured,checks=checks,throughput=throughput,common_native_pilot=pilot))
   write(out/'progress.json',dict(completed_phases=len(phases),last_method=name,last_state=state))
 free,total=torch.cuda.mem_get_info();assert free>=max(2*2**30,total*.15)
 write(out/'result.json',dict(case=c,block=block,status='PASS',initialization_reference_capture_s=init_s,card=card,qualification=qual,phases=phases,peak_reserved_bytes=torch.cuda.max_memory_reserved(),free_bytes=free,total_bytes=total,endpoint='128 real ready requests; CUDA event span and CPU submit-to-ready separately; cache preparation reported separately and available for total',actual_home_status='UNKNOWN; no address-home rule transferred from freed probe allocation'))
 print(c['id'],'PASS',len(phases),flush=True)
 scratch.close();del graphs,storage,calls,scratch;gc.collect();torch.cuda.empty_cache()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--family',choices=['sparse','inference','all'],default='all');p.add_argument('--block',type=int,default=0);p.add_argument('--profile',type=int,default=0);p.add_argument('--requests',type=int,default=128);p.add_argument('--out',type=Path,required=True);p.add_argument('--repeat-plan',type=Path);p.add_argument('--inspect-graph',action='store_true');a=p.parse_args();KEEP_GRAPH=a.inspect_graph
 cases=[]
 if a.family in ['sparse','all']:cases +=[dict(id=f'sparse_{m}_rhs{rhs}',matrix=m,rhs=rhs) for m in ['ca-GrQc','web-Google'] for rhs in [1,16]]
 if a.family in ['inference','all']:cases+=GEMM+ATTN
 plan=json.loads(a.repeat_plan.read_text())['repeats'] if a.repeat_plan else None
 for c in cases:run_case(c,a.block,a.out/c['id'],bool(a.profile),a.requests,plan)
