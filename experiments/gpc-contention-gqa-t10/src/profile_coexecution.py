import os,sys
os.environ['TEARDOWN_CUPTI']='0';os.environ['DISABLE_CUPTI_LAZY_REINIT']='1'
import control_e4
sys.modules['control']=control_e4
from gqa_runtime import *
from gemm_runtime import *
from measure import *
folder=Path(os.environ['T10_WORKER_DIR']);c=Control();plan=read(RUN/'freeze/resource_sets.json')['blocks'][0];pilot=read(RUN/'freeze/E4_NATIVE_ONLY_JOB.json');bgdata=GemmData(191800000);sharedbg=ck(z.gc_primary_stream());cid='GQA4_LONG';cc=dict(id=cid,B=1,H=32,HK=8,D=128,L=8192,lengths=[8192]);d=GQAData(cc,191810000,0);results=[]
placements={p['name']:p for p in plan['placements']};placements['NEUTRAL10_46']=plan['neutral']
def union_length(intervals):
 if not intervals:return 0.
 rr=sorted(intervals);start,end=rr[0];total=0.
 for a,b in rr[1:]:
  if a<=end:end=max(end,b)
  else:total+=end-start;start,end=a,b
 return total+end-start
for policy in ['SHARED56','NEUTRAL10_46','PACK_G0','SPREAD_0']:
 if policy=='SHARED56':fg,bg=0,sharedbg
 else:p=placements[policy];fg=c.create(p['foreground_sm_ids']);bg=c.create(p['background_complement_sm_ids'])
 d.reset();fj=GQAJob(d,True,'N19' if fg==0 else 'E56');bj=GemmJob(bgdata,bg);fgs,_=capture_ring(c,fg,fj,32);bgs,_=capture_ring(c,bg,bj,pilot[cid]['bg_gemms']);mix=MixedJob(fgs,bgs);mix.run(4)
 entry=dict(policy=policy,case=cid,kind='diagnostic_CUPTI_activity',memory_counters=None)
 try:
  with torch.profiler.profile(activities=[torch.profiler.ProfilerActivity.CPU,torch.profiler.ProfilerActivity.CUDA],record_shapes=False,profile_memory=False,with_stack=False) as prof:
   with torch.profiler.record_function('FIXED_MIXED_JOB_'+policy):mix.run(4)
  path=folder/(policy+'.json');prof.export_chrome_trace(str(path));events=read(path).get('traceEvents',[]);kernels=[x for x in events if x.get('cat')=='kernel' and x.get('ph')=='X']
  fge=[x for x in kernels if 'decode<' in x.get('name','') or 'merge<' in x.get('name','')];bge=[x for x in kernels if x not in fge]
  fi=[(x['ts'],x['ts']+x['dur']) for x in fge];bi=[(x['ts'],x['ts']+x['dur']) for x in bge];overlap=[(max(a,c1),min(b,d1)) for a,b in fi for c1,d1 in bi if max(a,c1)<min(b,d1)]
  entry.update(status='CAPTURED' if kernels else 'NA_NO_KERNEL_EVENTS',kernel_count=len(kernels),foreground_kernel_count=len(fge),background_kernel_count=len(bge),foreground_active_us=union_length(fi),background_active_us=union_length(bi),overlap_us=union_length(overlap),kernel_names=sorted({x['name'] for x in kernels}),streams=sorted({x.get('args',{}).get('stream',-1) for x in kernels}),trace_file=path.name)
 except Exception as e:entry.update(status='FAILED',error=repr(e))
 results.append(entry);write(folder/'PROFILES.json',results);mix.close();c.graph_drop(fgs);c.graph_drop(bgs);bj.close()
 if fg:c.drop(fg);c.drop(bg)
print('PROFILE_ATTEMPTS_COMPLETE',len(results),flush=True)
