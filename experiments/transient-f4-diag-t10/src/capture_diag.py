"""Six predeclared, separate CUPTI captures. Never used as formal effect timing."""
import os
os.environ['TEARDOWN_CUPTI']='0';os.environ['DISABLE_CUPTI_LAZY_REINIT']='1'
from diag import *
import sys,collections
out=Path(sys.argv[1]);bins=read(ROOT/'freeze/bins.json')
cases={c['id']:c for c in read(PRIOR/'input/T10_SELECTIVE_REORDER_REPAIR_V2_20261017/plans/cases.json')}
plans=[('AA_BURST_SLOT0','R_G017','LIB',False,'BURST_SLOT0'),('AA_READY_RING4','R_G017','LIB',False,'READY_RING4'),('F4_LL','V16','LIB',True,'READY_RING4'),('F4_SL','V16','SINGLE',True,'READY_RING4'),('V16_LIB','V16','LIB',False,'READY_RING4'),('V16_SINGLE','V16','SINGLE',False,'READY_RING4')]
records=[]
for index,(label,cid,action,chain,profile) in enumerate(plans):
 budget_check();c=cases[cid];e=Engine();d=Data(c['M'],c['N'],c['K'],ring=4,seed=910000+(1 if cid=='V16' else 0),chain=chain)
 js=[Job(e,d,slot=s,**config(action,c,bins,e)) for s in range(4)];qualify({action:js},d,out,label,'BEFORE')
 # The profiler is a separate observer. Fixed native conditioning finishes
 # before profiler entry; its entry gap and finite final conditioner are logged.
 ep=dict(id=label+'_PRECONDITION',case='F4' if chain else cid,block=0,conditioning=profile,windows=1,order='A')
 pre=episode(ep,js,js,1,out,seconds=30)
 n=read(ROOT/'freeze/PILOTS.json')['pilots']['R_G017']['n'] if cid=='R_G017' else 8
 raw=(Record*(12*2*n if cid=='R_G017' else 2*n))();history=(Record*192)();chunks=(Chunk*65536)();info=(C.c_int64*12)();nw=12 if cid=='R_G017' else 1;labels='ABBABAABABBA'[:nw]
 enter=time.monotonic_ns()
 with torch.profiler.profile(activities=[torch.profiler.ProfilerActivity.CPU,torch.profiler.ProfilerActivity.CUDA]) as prof:
  active=time.monotonic_ns()
  check(lib.diag_episode(ptr(js),ptr(js),PROFILES.index(profile),0.000001,n,nw,(I*nw)(*[int(x=='B') for x in labels]),0,0,raw,history,chunks,65536,info))
  end=time.monotonic_ns()
 hh={x.global_index:x for x in history if x.end}
 if hh:
  for x in hh.values():x.action=1 if action=='SINGLE' else 0
  save_csv(out/(label+'.profile.conditioning_edges.csv.gz'),output_rows([hh[k] for k in sorted(hh)],dict(id=label,case='F4' if chain else cid,block=0,n=n,conditioning=profile),'conditioning'))
 prof.export_chrome_trace(str(out/(label+'.chrome.json')))
 events=read(out/(label+'.chrome.json'))['traceEvents'];kernels=[x for x in events if x.get('cat')=='kernel'];api=[x for x in events if x.get('cat') in ['cuda_runtime','cuda_driver']]
 rec=dict(label=label,case=cid,chain=chain,action=action,profile=profile,precondition_end_ns=pre['measurement_end_ns'],profiler_entry_begin_ns=enter,profiler_active_ns=active,capture_end_ns=end,conditioning_to_capture_gap_ns=active-pre['measurement_end_ns'],actual_capture='one finite64-request final conditioning packet plus recorded windows; preceding30s not captured',window_n=n,window_count=nw,kernel_events=kernels,api_events=api,api_counts=dict(collections.Counter(x['name'] for x in api)),memcpy_events=[x for x in events if 'memcpy' in x.get('cat','').lower()],metadata=meta(js,e,d),scope='Independent profiled activity only; formal timing excludes profiler; same-seed/dimensions but freshly allocated data across capture conditions within this profiling worker')
 save_csv(out/(label+'.profile_requests.csv.gz'),output_rows(raw,dict(id=label,case='F4' if chain else cid,block=0,n=n,conditioning=profile)))
 write(out/(label+'.capture_conditioning.json'),dict(info=list(info),chunks=[{k:getattr(x,k) for k,_ in Chunk._fields_} for x in list(chunks)[:info[3]]]))
 qualify({action:js},d,out,label,'AFTER',all_slots=False);records.append(rec);write(out/'captures.json',records)
 for j in js:j.close()
 d.close();e.close();print(label,'CAPTURED',len(kernels),'kernels',flush=True)
write(out/'complete.json',dict(status='PASS',captures=len(records)))
