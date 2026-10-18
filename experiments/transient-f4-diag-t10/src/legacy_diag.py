"""Late supplementary original Python batch64 replay; preserve fidelity differences."""
from diag import *
import sys
out=Path(sys.argv[1]);block=int(sys.argv[2]);c=next(x for x in read(PRIOR/'input/T10_SELECTIVE_REORDER_REPAIR_V2_20261017/plans/cases.json') if x['id']=='R_G017');bins=read(ROOT/'freeze/bins.json')
e=Engine(mode=-1,diagnostic=False);d=Data(c['M'],c['N'],c['K'],ring=4,seed=930000+block,workspace_words=max(workspace_for(a,c,bins) for a in ACTIONS));jobs={a:[Job(e,d,slot=s,**config(a,c,bins,e)) for s in range(4)] for a in ACTIONS};qualify(jobs,d,out,'LEGACY','BEFORE');write(out/'graphs.json',{a:meta(js,e,d) for a,js in jobs.items()})
chunks=np.empty((65536,5),dtype=np.float64);count=0;nc=0;start=time.monotonic_ns()
while (time.monotonic_ns()-start)/1e9<30:
 assert nc<len(chunks);a=time.monotonic_ns();v=jobs['LIB'][count%4].batch(64);b=time.monotonic_ns();chunks[nc]=[a-start,b-start,count,v[0],v[1]];nc+=1;count+=64;budget_check()
end=time.monotonic_ns()

n=read(ROOT/'freeze/PILOTS.json')['pilots']['R_G017']['n'];ep=dict(id=f'LEGACY_SUPPLEMENT_{block}',kind='legacy_supplement',case='R_G017',block=block,fixture='ALL_ACTIONS_RESIDENT',conditioning='BURST_SLOT0',windows=12,external_legacy_conditioning_end_ns=end,reason='Supplement after code-fidelity review; not preplanned independentD4 sample')
episode(ep,jobs['LIB'],jobs['LIB'],n,out,seconds=0)
write(out/'legacy_conditioning.json',dict(kind='ORIGINAL_PYTHON_JOB_BATCH64_SLOT0',start_ns=start,end_ns=end,replays=count,slot_histogram=[count,0,0,0],actual_seconds=(end-start)/1e9,chunks=[dict(begin_offset_ns=int(x[0]),ready_offset_ns=int(x[1]),first_request=int(x[2]),batch_gpu_span_us=x[3],batch_cpu_us=x[4]) for x in chunks[:nc]],scope='Old jobs[count%4].batch(64); count+=64, including original outer batch events and Python boundary; extra host timestamps/log buffer capture is disclosed. No new roster probing.'))
qualify(jobs,d,out,'LEGACY','AFTER',all_slots=False)
for js in jobs.values():
 for j in js:j.close()
d.close();e.close();write(out/'complete.json',dict(status='PASS',scope='Original batch64 conditioning call path; formal request instrumentation remains new. Legacy S4 prior roster history and old n not recreated.'))
