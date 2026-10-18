"""Late discovered library reference: fixed descriptors, same buffers and fusion."""
import argparse,gc,hashlib,inspect,json,pathlib,time,traceback
import torch
from native_bench import ROOT,grouped,layer,phase,write,mm_reference,check
from request_layer_bench import measure
from grouped_library import Grouped,capture_readable,LIBRARY
from reference import balanced_orders

def make_layer(case,block):
 ordinary,validate,ledger,storage=layer(case,block)
 v=inspect.getclosurevars(ordinary).nonlocals
 aa=[];bb=[];cc=[];dd=[];ee=[];ff=[]
 for j in range(v['e']):
  lo,hi=v['offset'][j:j+2]
  if lo<hi:
   aa.append(v['pack'][lo:hi]);bb.append(v['wgu'][j]);cc.append(v['gu'][lo:hi])
   dd.append(v['act'][lo:hi]);ee.append(v['wd'][j]);ff.append(v['down'][lo:hi])
 up=Grouped(aa,bb,cc);down=Grouped(dd,ee,ff)
 def native():
  torch.index_select(v['x'],0,v['token'],out=v['pack']);up()
  torch.ops.aten.silu.out(v['gu'][:,:v['i']],out=v['silu']);torch.mul(v['silu'],v['gu'][:,v['i']:],out=v['act'])
  down();torch.index_select(v['down'],0,v['inv'],out=v['unpack'])
  torch.mul(v['unpack'].view(v['t'],v['top'],v['h']),v['gates'][:,:,None],out=v['weighted'])
  torch.sum(v['weighted'],dim=1,out=v['output'])
 return ordinary,native,validate,ledger,storage

def case_run(case,block,request):
 torch.manual_seed(2026101517+block%3);torch.cuda.reset_peak_memory_stats();start=time.perf_counter()
 if request:ordinary,native,validate,ledger,storage=make_layer(case,block)
 else:
  ordinary,validate,ledger,storage=grouped(case,block)
  native=Grouped(storage['inputs'],storage['weights'],storage['outputs'])
 ordinary();assert all(x['pass'] for x in validate())
 native();torch.cuda.synchronize();qualification=validate();assert all(x['pass'] for x in qualification),qualification
 oldgraph,oldnodes=capture_readable(ordinary);newgraph,newnodes=capture_readable(native)
 # Both paths replay into the identical output buffers checked by the same FP64 reference.
 for graph in [oldgraph,newgraph]:
  graph.replay();torch.cuda.synchronize();assert all(x['pass'] for x in validate())
 calls={'PER_EXPERT_GRAPH':oldgraph.replay,'NATIVE_GROUPED_GRAPH':newgraph.replay}
 order=balanced_orders(list(calls),6,2026101517)[block]
 rows=[]
 for name,role in [('PER_EXPERT_GRAPH','anchor_head')]+[(n,'primary') for n in order]+[('PER_EXPERT_GRAPH','anchor_tail')]:
  measured=measure(calls[name]) if request else phase(calls[name],128)
  checks=validate();assert all(x['pass'] for x in checks),checks
  rows.append(dict(variant=name,phase_role=role,correctness=checks,status='COMPLETED',**measured))
 return dict(case=case,block=block,status='STRONG_LIBRARY_BASELINE_ONLY',candidate_status='NOT_IMPLEMENTED',phases=rows,ledger=ledger,native_grouped_ledger=dict(gemm_api_calls=2 if request else 1,metadata_scope='HOST_STATIC_DESCRIPTORS_DEVICE_POINTER_ARRAYS; setup outside timed hot replay',descriptor_rebuild_timed=False,new_scheduler=False,library=LIBRARY),graph_structure={'PER_EXPERT_GRAPH':oldnodes,'NATIVE_GROUPED_GRAPH':newnodes},scope='POST_ROUTE_FIXED_COUNTS_TRUE_REQUEST_READY' if request else 'OP_RESIDENT_AMORTIZED',qualification=qualification,elapsed_s=time.perf_counter()-start,peak_reserved_bytes=torch.cuda.max_memory_reserved(),free_bytes_after=torch.cuda.mem_get_info()[0])

def qualify(out):
 # Changed-input, poisoned-output test on the very same captured graph.
 torch.manual_seed(2026101517)
 aa=[torch.randn(m,128,device='cuda',dtype=torch.float16) for m in [0,1,17,64,17,64,1]]
 bb=[torch.randn(128,256,device='cuda',dtype=torch.float16) for a in aa]
 cc=[torch.empty(a.shape[0],256,device='cuda',dtype=torch.float16) for a in aa]
 native=Grouped(aa,bb,cc);g,nodes=capture_readable(native);checks=[]
 for j in range(3):
  for a,c in zip(aa,cc):a.normal_();c.fill_(float('nan'))
  g.replay();torch.cuda.synchronize()
  tests=[check(c,mm_reference(a,b)) for a,b,c in zip(aa,bb,cc) if a.numel()]
  checks.append(dict(replay=j,checks=tests));assert all(x['pass'] for x in tests),tests
 # Also exercise the zero-edge single-kernel graph audit boundary.
 one=Grouped([aa[1]],[bb[1]],[cc[1]]);onegraph,onenodes=capture_readable(one)
 onegraph.replay();torch.cuda.synchronize();onecheck=check(cc[1],mm_reference(aa[1],bb[1]));assert onecheck['pass']
 write(out/'qualification.json',dict(status='SUPPORTED_NUMERICAL_AND_GRAPH',empty_expert_handled=True,group_count=native.e,group_sizes=list(native.sizes),problem_count=native.problem_count,changed_input_poisoned_output_checks=checks,graph_structure=nodes,single_kernel_graph=onenodes,single_kernel_check=onecheck,math_mode=16,compute_type=68,closed_library=True,candidate_implemented=False))

def main(a):
 torch.backends.cuda.preferred_blas_library('cublas')
 sources=['strong_bench.py','grouped_library.py','native_bench.py','request_layer_bench.py']
 write(a.out/'runtime.json',dict(torch=torch.__version__,cuda=torch.version.cuda,shared_sources={n:hashlib.sha256((ROOT/'tools'/n).read_bytes()).hexdigest() for n in sources}))
 for n in sources:(a.out/('dependency_'+n)).write_bytes((ROOT/'tools'/n).read_bytes())
 if a.qualify:return qualify(a.out)
 selected=json.loads((ROOT/'preregistration/strong_library_cohort.json').read_text())['selection'][a.stage]
 cases=[json.loads(line) for line in (ROOT/'preregistration/plan.jsonl').read_text().splitlines() if json.loads(line)['case_id'] in selected]
 for case in cases:
  try:r=case_run(case,a.block,a.stage=='E4')
  except Exception as ex:
   if any(s in str(ex) for s in ['illegal memory access','device-side assert','unspecified launch failure']):raise
   r=dict(case=case,block=a.block,status='FAILED',error=str(ex),traceback=traceback.format_exc())
  gc.collect();torch.cuda.empty_cache();r['free_after_cleanup']=torch.cuda.mem_get_info()[0]
  write(a.out/(case['case_id']+'.json'),r);print(case['case_id'],r['status'],round(r.get('elapsed_s',0),2),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--stage');p.add_argument('--block',type=int,default=0);p.add_argument('--qualify',action='store_true');p.add_argument('--out',type=pathlib.Path,required=True);main(p.parse_args())
