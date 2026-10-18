"""Fixed six held-out layer cases: true output-ready boundary per request."""
import argparse,gc,hashlib,json,math,pathlib,time
import torch
from native_bench import ROOT,layer,capture,utc,write
from reference import balanced_orders

def measure(fn):
 a=torch.cuda.Event(enable_timing=True);b=torch.cuda.Event(enable_timing=True)
 def once():
  t=time.perf_counter();a.record();fn();b.record();b.synchronize()
  return a.elapsed_time(b),(time.perf_counter()-t)*1000
 warm=0;warmms=0.;start=utc()
 while warm<64 or warmms<300:
  d,_=once();warm+=1;warmms+=d
 samples=[once() for _ in range(128)]
 return dict(start=start,end=utc(),warmup_repeats=warm,warmup_device_ms=warmms,measured_requests=128,device_interval_ms=sum(x[0] for x in samples)/128,operator_or_layer_ready_ms=sum(x[1] for x in samples)/128,request_device_ms=[x[0] for x in samples],request_ready_ms=[x[1] for x in samples],endpoint='ONE_OUTPUT_READY_SYNCHRONIZATION_PER_REQUEST',instrumentation='two preallocated CUDA events plus one result-boundary synchronization per request',p99_claim=None)

def main(args):
 torch.backends.cuda.preferred_blas_library('cublas')
 ids=['moe_layer-007','moe_layer-008','moe_layer-009','moe_layer-016','moe_layer-017','moe_layer-024']
 cases=[json.loads(x) for x in (ROOT/'preregistration/plan.jsonl').read_text().splitlines() if json.loads(x)['case_id'] in ids]
 write(args.out/'runtime.json',dict(torch=torch.__version__,cuda=torch.version.cuda,shared_math_source_sha256=hashlib.sha256((ROOT/'tools/native_bench.py').read_bytes()).hexdigest(),no_math_change_from_native_layer=True,scope='SYNTHETIC_POST_ROUTE_FIXED_COUNTS_HOT_REQUESTS'))
 for c in cases:
  start=time.perf_counter();torch.manual_seed(2026101517+args.block%3);torch.cuda.reset_peak_memory_stats()
  calls=g=fn=validate=storage=None
  free_before_case=torch.cuda.mem_get_info()[0]
  try:
   fn,validate,ledger,storage=layer(c,args.block)
   assert all(x['pass'] for x in validate())
   g,_=capture(fn);g.replay();torch.cuda.synchronize();assert all(x['pass'] for x in validate())
   calls={'CUBLAS_GRAPH_REQUEST':g.replay,'CUBLAS_EAGER_REQUEST':fn};order=balanced_orders(list(calls),6,2026101517)[args.block]
   phases=[('CUBLAS_GRAPH_REQUEST','anchor_head')]+[(x,'primary') for x in order]+[('CUBLAS_GRAPH_REQUEST','anchor_tail')]
   rows=[]
   for name,role in phases:
    result=measure(calls[name]);checks=validate();passed=all(x['pass'] for x in checks)
    rows.append(dict(variant=name,phase_role=role,correctness=checks,status='COMPLETED' if passed else 'NUMERICAL_FAILED',**result))
    assert passed
   out=dict(case=c,block=args.block,status='BASELINE_REQUEST_LATENCY_ONLY',candidate_status='NOT_IMPLEMENTED',ledger=ledger,phases=rows,elapsed_s=time.perf_counter()-start,peak_reserved_bytes=torch.cuda.max_memory_reserved(),free_bytes_after=torch.cuda.mem_get_info()[0])
  except (MemoryError,torch.OutOfMemoryError) as e:out=dict(case=c,block=args.block,status='MEMORY_UNSUPPORTED',error=str(e))
  # Do not call locals(): on Python3.12 its cached dict can retain these closures.
  calls=g=fn=validate=storage=None
  _=None
  gc.collect();torch.cuda.empty_cache()
  out['free_before_case']=free_before_case;out['free_after_cleanup']=torch.cuda.mem_get_info()[0]
  write(args.out/(c['case_id']+'.json'),out);print(c['case_id'],out['status'],round(out.get('elapsed_s',0),2),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--block',type=int,required=True);p.add_argument('--out',type=pathlib.Path,required=True);main(p.parse_args())
