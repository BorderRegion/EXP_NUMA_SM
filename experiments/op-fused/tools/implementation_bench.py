"""Actual grouped CORE/CACHE/FULL comparisons; original inputs and budget."""
import argparse,gc,hashlib,json,math,os,pathlib,time,traceback
import torch
from native_bench import ROOT,grouped,phase,check,capture,utc
from cutlass_grouped import CutlassGrouped
from grouped_library import Grouped,capture_readable
from reference import balanced_orders,Problem,make_packets

SEEDS=[2026101531,2026101543,2026101557,2026101571,2026101587,2026101601]

def packet_stats(op):
 bm=op.resource_table[0]['tile_m'];problems=[Problem(m,n,k) for m,n,k in op.shapes]
 if op.mode==2:
  packets=make_packets(problems,bm,128,32,op.workers,op.q_cap,op.waves,128)
  counts={}
  for p in packets:counts[str(p.length)]=counts.get(str(p.length),0)+1
  return dict(packets=len(packets),length_counts=counts,tiles=sum(p.length for p in packets),
              has_multitile_packet=any(p.length>1 for p in packets))
 return None

def specs(calibration,freeze):
 if calibration:
  result={}
  for r in [0,1]:
   result[f'CORE_r{r}']=(r,0,1,1,False)
   for q in [1,2,4]:result[f'CACHE_r{r}_q{q}']=(r,1,q,1,False)
   for q in [1,2,4]:
    for w in [1,2]:result[f'FULL_r{r}_q{q}_w{w}']=(r,2,q,w,False)
  return result
 r=freeze['recipe'];q,w=freeze['full_q'],freeze['full_waves']
 return dict(CORE=(r,0,1,1,False),CACHE=(r,1,freeze['cache_q'],1,False),
             FULL=(r,2,q,w,False),ABL=(r,2,1,w,False),BAL=(r,0,1,1,True))

def run_case(case,block,calibration,freeze):
 torch.manual_seed(SEEDS[block]+int(case['case_id'].split('-')[-1]))
 torch.cuda.reset_peak_memory_stats();start=time.perf_counter()
 ordinary,validate,ledger,storage=grouped(case,block)
 aa,bb,cc=storage['inputs'],storage['weights'],storage['outputs']
 expected={}
 for r in ([0,1] if calibration else [freeze['recipe']]):
  core=CutlassGrouped(aa,bb,cc,r,0);core();torch.cuda.synchronize()
  assert all(c['pass'] for c in validate())
  expected[r]=[c.clone() for c in cc];core.close()
 variants={};objects=[];metadata={};aliases={};recipe_for={};graphs={};seen={}
 requests=specs(calibration,freeze)
 for name,parameters in requests.items():
  r,mode,q,w,sort_k=parameters
  if sort_k and len({a.shape[1] for a in aa})==1:parameters=(r,mode,q,w,False)
  if parameters in seen:
   aliases[name]=seen[parameters];continue
  seen[parameters]=name
  obj=CutlassGrouped(aa,bb,cc,r,mode,q,w,sort_k=parameters[-1])
  obj();torch.cuda.synchronize()
  assert all(torch.equal(c,e) for c,e in zip(cc,expected[r])),name
  graph,nodes=capture_readable(obj)
  variants[name]=graph.replay;objects.append(obj);graphs[name]=graph
  metadata[name]=dict(adapter=obj.metadata(),packets=packet_stats(obj),graph_structure=nodes)
  recipe_for[name]=r
 lib_names=['PER_EXPERT_GRAPH','NATIVE_GROUPED_GRAPH'] if calibration else [freeze['library']]
 native=Grouped(aa,bb,cc) if 'NATIVE_GROUPED_GRAPH' in lib_names else None
 for name in lib_names:
  call=ordinary if name=='PER_EXPERT_GRAPH' else native
  graph,nodes=capture_readable(call);graphs[name]=graph;variants[name]=graph.replay
  metadata[name]=dict(graph_structure=nodes,library_reference=True)
 anchor='PER_EXPERT_GRAPH' if calibration else freeze['library']
 pilot=phase(variants[anchor],128)
 repeats=max(128,min(512,math.ceil(75/max(pilot['device_interval_ms'],1e-6))))
 order=balanced_orders(list(variants),6,2026101531)[block]
 rows=[]
 for name,role in [(anchor,'anchor_head')]+[(n,'primary') for n in order]+[(anchor,'anchor_tail')]:
  measurements=phase(variants[name],repeats)
  checks=validate();assert all(x['pass'] for x in checks),(name,checks)
  exact=all(torch.equal(c,e) for c,e in zip(cc,expected[recipe_for[name]])) if name in recipe_for else None
  if exact is not None:assert exact,name
  rows.append(dict(variant=name,phase_role=role,correctness=checks,same_body_bitwise=exact,**measurements))
 free,total=torch.cuda.mem_get_info();reserved=torch.cuda.max_memory_reserved()
 result=dict(status='IMPLEMENTED_OPERATOR_COMPARISON',case=case,block=block,input_seed=SEEDS[block]+int(case['case_id'].split('-')[-1]),
   phases=rows,metadata=metadata,aliases=aliases,ledger=ledger,elapsed_s=time.perf_counter()-start,
   measured_repeats=repeats,pilot=pilot,memory=dict(peak_reserved_bytes=reserved,free_after=free,total=total,
   conservative_margin_pass=reserved<=total-max(2*2**30,math.ceil(.15*total))),
   scope='SYNTHETIC_STATIC_GROUPED_OPERATOR_GRAPH_AMORTIZED',candidate_implemented=True,
   source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'src').glob('*') if p.is_file()})
 for obj in objects:obj.close()
 return result

def main(args):
 torch.set_num_threads(2);torch.backends.cuda.preferred_blas_library('cublas')
 torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cuda.matmul.allow_fp16_reduced_precision_reduction=False
 calibration=args.stage=='E1'
 freeze=None if calibration else json.loads((ROOT/'preregistration/implementation_freeze.json').read_text())
 plans=[json.loads(s) for s in (ROOT/'preregistration/plan.jsonl').read_text().splitlines()]
 if calibration:cases=[c for c in plans if c['suite']=='grouped' and c['split']=='calibration']
 else:
  ids=freeze['test_case_ids'];cases=[c for c in plans if c['case_id'] in ids]
 if args.limit:cases=cases[:args.limit]
 runtime=dict(torch=torch.__version__,cuda=torch.version.cuda,seed=SEEDS[args.block],block=args.block,
     power_regime='FIXED_100W_WITH_ORIGINAL_FAN_AND_PROTECTION',calibration=calibration,
     carryover='six fixed balanced-order rows; incomplete full carryover cycle when variants>6',
     aggregate_scope='CUDA event span not busy time; bounded repeats can be below 50ms',
     memory_scope='all graph variants share inputs/output; refs and same-core expected buffers recorded')
 (args.out/'runtime.json').write_text(json.dumps(runtime,indent=2)+'\n')
 for case in cases:
  try:result=run_case(case,args.block,calibration,freeze)
  except (MemoryError,torch.OutOfMemoryError) as e:
   result=dict(status='MEMORY_UNSUPPORTED',case=case,block=args.block,error=str(e))
  (args.out/(case['case_id']+'.json')).write_text(json.dumps(result,indent=2)+'\n')
  print(case['case_id'],result['status'],round(result.get('elapsed_s',0),2),flush=True)
  gc.collect();torch.cuda.empty_cache()

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=pathlib.Path)
 p.add_argument('--stage',choices=['E1','E3'],required=True);p.add_argument('--block',type=int,required=True)
 p.add_argument('--limit',type=int,default=0);main(p.parse_args())
