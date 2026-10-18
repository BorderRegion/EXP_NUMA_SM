from runtime import *
import sys
out=Path(sys.argv[1]);rng=np.random.default_rng(124000000);rows=[];checks=[];selected=read(ROOT/'freeze/SELECTION.json')['choices']
for V in [131072,129024]:
 d=Data(V,124000000+V)
 for variant in VARIANTS:
  for scope in ['ready','fresh']:
   choice=selected[f'{V}|{variant}|17|{scope}']['policy'];names=['MINIMAX','IDENTITY','POOLED','WRONG_ADDRESS',choice];jobs={n:[Job(d,s,variant,n,17,scope,True) for s in range(4)] for n in names};raw=[]
   for b in range(16):
    for n in rng.permutation(names):
     j=jobs[n][b%4];j.run(1);pr=d.prof.cpu().numpy().copy();tr=d.trace.cpu().view(56,2).numpy();assert np.array_equal(np.sort(tr[:,0]),np.arange(56)) and np.array_equal(tr[:,0],tr[:,1]);col=np.flatnonzero(pr[:,6]);assert len(col)==1
     if variant in ['FIX','BOTH']:assert col.tolist()==[1]
     checks.append(dict(V=V,variant=variant,scope=scope,policy=n,block=b,**d.check(b%4)));raw.append(pr);rows.append(dict(V=V,variant=variant,scope=scope,policy=n,block=b,collector=int(col[0]),local_median_ns=float(np.median(pr[:,4]-pr[:,3])),local_spread_ns=int(np.ptp(pr[:,4])),consumer_handoff_median_ns=float(np.median(pr[1::2,5]-pr[1::2,4])),collector_wait_ns=int(pr[col[0],6]-pr[col[0],5]),collector_reduce_ns=int(pr[col[0],7]-pr[col[0],6]),thread0_span_ns=int(pr[:,8].max()-pr[:,3].min()),work_min=int(pr[:,2].min()),work_max=int(pr[:,2].max())))
   np.save(out/f'trace_{V}_{variant}_{scope}.npy',np.array(raw))
   for js in jobs.values():
    for j in js:j.close()
 d.close()
write(out/'numerical.json',checks);write(out/'trace_summary.json',rows);write(out/'complete.json',dict(status='PASS',checks=len(checks),warning='Instrumented diagnostic kernel; timestamps/stores perturb schedule; thread0 span is not uninstrumented full kernel latency.'))
