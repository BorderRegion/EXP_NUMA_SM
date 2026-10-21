import os
os.environ['TEARDOWN_CUPTI']='0';os.environ['DISABLE_CUPTI_LAZY_REINIT']='1'
from campaign_runtime import *
folder=Path(os.environ['T10_WORKER_DIR']);chosen=read(RUN/'freeze/SELECTION.json');results=[]
for cid in ['LONG','RAGGED']:
 s=Suite(cid,2);a=dict(chosen[cid]['PC_STAR']['action'],mode='RELEASE');p=s.plan(a,diagnostic=True);s.d.reset();p.run(4);r=p.run(4);check=p.check()
 results.append(dict(case=cid,kind='INDEPENDENT_RELEASE_TIMESTAMPS',action=a,metrics=METRICS,rows=r.tolist(),check=check,meta=p.meta,not_formal_performance=True))
 assert (r[:,6]+2>=np.maximum(r[:,4],r[:,2])).all()
 write(folder/f'{cid}_DAG_PROVENANCE.json',s.provenance());s.close()
s=Suite('LONG',2);a=dict(chosen['LONG']['PC_STAR']['action'],mode='RELEASE')
plans={'SHARED56':s.plan(native('SHARED56')),'RELEASE':s.plan(a),'BG_PRIMARY56':s.solo('BG','PRIMARY56'),'BG_GREEN46':s.solo('BG','SPREAD_Q10')};profiles=[]
for label,p in plans.items():
 s.d.reset();p.run(4)
 with torch.profiler.profile(activities=[torch.profiler.ProfilerActivity.CPU,torch.profiler.ProfilerActivity.CUDA]) as prof:p.run(2)
 path=folder/(label+'.json');prof.export_chrome_trace(str(path));trace=read(path)
 kernels=[x for x in trace['traceEvents'] if x.get('cat')=='kernel'];assert kernels
 profiles.append(dict(label=label,kernel_count=len(kernels),kernel_names=sorted({x['name'] for x in kernels}),streams=sorted({x.get('args',{}).get('stream') for x in kernels if x.get('args',{}).get('stream') is not None}),trace_file=path.name,memory_hardware_counters=None,formal_performance=False))
 results.append(dict(kind='PROFILE_OUTPUT_CHECK',label=label,check=p.check(1)))
write(folder/'TIMESTAMPS_AND_CHECKS.json',results);write(folder/'PROFILES.json',profiles);write(folder/'COMPLETE.json',dict(status='PASS',CUPTI_captures=len(profiles),release_cases=2));s.close();print('DIAGNOSTICS_COMPLETE',flush=True)
