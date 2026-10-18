"""Native lifecycle costs only. An unvalidated map is never replayed."""
import argparse,gc,time
import torch
from common import *
from native_ops import capture,check,mm_ref
p=argparse.ArgumentParser();p.add_argument('--block',type=int,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
t=time.perf_counter();torch.cuda.init();device_init_s=time.perf_counter()-t;events=[]
for generation,(name,n) in enumerate([('INITIAL_ALLOCATION',2048),('REALLOCATE_SAME_CAPACITY',2048),('CAPACITY_GROW',4096)]):
 torch.manual_seed(2026101691+a.block*11+generation);start=time.perf_counter()
 x=torch.randn(64,1024,device='cuda',dtype=torch.float16)/32;w=torch.randn(1024,n,device='cuda',dtype=torch.float16);torch.cuda.synchronize();allocation_input_s=time.perf_counter()-start
 ptrs=[x.data_ptr(),w.data_ptr()];t=time.perf_counter();ref=mm_ref(x,w);torch.cuda.synchronize();reference_s=time.perf_counter()-t
 def fn():return torch.mm(x,w)
 t=time.perf_counter();g,y=capture(fn);g.replay();torch.cuda.synchronize();capture_s=time.perf_counter()-t;qualified=check(y,ref);assert qualified['pass_']
 e0=torch.cuda.Event(enable_timing=True);e1=torch.cuda.Event(enable_timing=True)
 for _ in range(64):g.replay()
 torch.cuda.synchronize();samples=[]
 for _ in range(128):
  t=time.perf_counter();e0.record();g.replay();e1.record();e1.synchronize();samples.append([e0.elapsed_time(e1),(time.perf_counter()-t)*1000])
 q=check(y,ref);assert q['pass_'];events.append(dict(event=name,generation=generation,shape=[64,n,1024],pointers=ptrs,allocation_and_input_generation_s=allocation_input_s,reference_s=reference_s,capture_s=capture_s,checks=[qualified,q],requests=128,samples_columns=['event_ms','cpu_ready_ms'],samples=samples,method='N_CUBLAS',compiled_affinity_rule=None,previous_graph_destroyed_before_allocation=True,old_rule_reuse=False,note='Reallocated VA may repeat; generation is distinct. No valid affinity model exists in this baseline diagnostic.'))
 del g,y,x,w,ref,fn,e0,e1;gc.collect();torch.cuda.empty_cache();write(a.out/'lifecycle.json',dict(status='PASS',block=a.block,device_initialization_s=device_init_s,events=events,scope='SYNTHETIC_NATIVE_GEMM_ONLY; not lifecycle validation of an absent NUMA method'))
