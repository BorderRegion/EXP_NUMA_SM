import os
os.environ['TEARDOWN_CUPTI']='0';os.environ['DISABLE_CUPTI_LAZY_REINIT']='1'
from deploy import *
import sys
out=Path(sys.argv[1]);records=[]
def capture(label,p):
 warm([p]);path=out/(label+'.json')
 with torch.profiler.profile(activities=[torch.profiler.ProfilerActivity.CPU,torch.profiler.ProfilerActivity.CUDA]) as prof:
  for i in range(8):check(lib.sr_run_async(p.jobs[i%4].ptr));check(lib.sr_wait(p.e.ptr))
 prof.export_chrome_trace(str(path));events=read(path)['traceEvents'];kernels=[x for x in events if x.get('cat')=='kernel'];copies=[x for x in events if 'memcpy' in x.get('cat','').lower()];apis=collections.Counter(x['name'] for x in events if x.get('cat') in ['cuda_runtime','cuda_driver']);records.append(dict(label=label,status='CAPTURED',kernel_events=kernels,memcpy_events=copies,cuda_api_counts=dict(apis),plan=p.metadata(),correctness=p.d.numerical(3),scope='Eight actual uninstrumented-body asynchronous graph submissions, caller waits at output boundary. CUPTI capture separate from formal timings; no hardware memory counters.'))
import collections
cases={c['id']:c for c in read(INPUT/'plans/cases.json')}
p=BoundPlan(cases['T01'],'RESOURCE',seed=320001);capture('NATIVE_RESOURCE_EXIT',p);p.close()
p=BoundPlan(cases['T12'],'PERMUTED_RESOURCE',seed=320002);capture('SELECTED_PC_PERMUTED',p);p.close()
f=read(INPUT/'plans/ffn_chains.json')[0];c=dict(id=f['id'],M=f['M'],N=f['intermediate'],K=f['hidden']);p=BoundPlan(c,'RESOURCE',seed=320003,chain=True);capture('FFN_NATIVE_EXIT',p);p.close()
write(out/'profiles.json',records);write(out/'complete.json',dict(status='PASS',captures=3))
