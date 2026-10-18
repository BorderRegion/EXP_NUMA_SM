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
for i,cid in enumerate(['V01','V06','V11','V16']):
 p=BoundPlan(cases[cid],'RESOURCE',seed=360000+i,dynamic=False);capture(cid+'_RESOURCE',p);p.close()
write(out/'profiles.json',records);write(out/'complete.json',dict(status='PASS',captures=4))
