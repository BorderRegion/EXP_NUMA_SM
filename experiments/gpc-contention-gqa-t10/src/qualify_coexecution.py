import sys
import control_e4
sys.modules['control']=control_e4
from gqa_runtime import *
from gemm_runtime import *
from measure import *
import os
folder=Path(os.environ['T10_WORKER_DIR']);c=Control();plan=read(RUN/'freeze/resource_sets.json')['blocks'][0];bgdata=GemmData(190700000);sharedbg=ck(z.gc_primary_stream());checks=[];pilot={}
# Only native all-resource data determine the fixed useful-work ratio.
gj=GemmJob(bgdata,sharedbg);graphs,_=capture_ring(c,sharedbg,gj,1);warm(c,graphs,1);bt=c.run(graphs,16)
for slot in range(4):c.run([graphs[slot]],1);checks.append(dict(task='native_gemm',slot=slot,**bgdata.check(slot)))
tbg=float(np.median(bt[:,0]));c.graph_drop(graphs);gj.close()
for cid in ['GQA4_LONG','BATCH4_RAGGED']:
 arg=next(x for x in read(RUN/'freeze/experiment_plan.json')['gqa_cases'] if x['id']==cid)
 cc=dict(id=cid,B=arg['B'],H=arg['Hq'],HK=arg['Hkv'],D=128,L=max(arg['lengths']),lengths=arg['lengths']);d=GQAData(cc,190710000+cc['L'],0);j=GQAJob(d,True,'N19');gg,_=capture_ring(c,0,j,1);warm(c,gg,1);ft=c.run(gg,16);c.graph_drop(gg)
 tfg=float(np.median(ft[:,0]));count=max(1,min(64,int(np.floor(32*tfg/tbg+.5))));pilot[cid]=dict(fg_requests=32,bg_gemms=count,native_fg_gpu_us=tfg,native_bg_gpu_us=tbg,foreground_mode='VALUE_CHANGING_FIXED_LENGTH_APPEND_ATTENTION')
 d.close()
write(RUN/'freeze/E4_NATIVE_ONLY_JOB.json',pilot)
# Actual cuBLAS background and GQA qualify concurrently in each placement.
for cid in ['GQA4_LONG','BATCH4_RAGGED']:
 arg=next(x for x in read(RUN/'freeze/experiment_plan.json')['gqa_cases'] if x['id']==cid);cc=dict(id=cid,B=arg['B'],H=arg['Hq'],HK=arg['Hkv'],D=128,L=max(arg['lengths']),lengths=arg['lengths']);d=GQAData(cc,190720000+cc['L'],0)
 placements=[dict(name='SHARED56',foreground_sm_ids=list(range(56)),background_complement_sm_ids=list(range(56)))]+plan['placements']+[plan['neutral']]
 for p in placements:
  if p['name']=='SHARED56':fg,bg=0,sharedbg
  else:fg=c.create(p['foreground_sm_ids']);bg=c.create(p['background_complement_sm_ids']);c.verify(fg,p['foreground_sm_ids']);c.verify(bg,p['background_complement_sm_ids'])
  d.reset();fj=GQAJob(d,True,'N19' if fg==0 else 'E56');bj=GemmJob(bgdata,bg);fgs,_=capture_ring(c,fg,fj,32);bgs,_=capture_ring(c,bg,bj,pilot[cid]['bg_gemms']);mix=MixedJob(fgs,bgs)
  a=mix.run(4);flast=(3+31)%4;blast=(3+pilot[cid]['bg_gemms']-1)%4
  checks.append(dict(case=cid,policy=p['name'],task='foreground',**d.check_mode(True,flast)))
  checks.append(dict(case=cid,policy=p['name'],task='background',**bgdata.check(blast)))
  mix.close();c.graph_drop(fgs);c.graph_drop(bgs);bj.close()
  if fg:c.drop(fg);c.drop(bg)
  write(folder/'NUMERICAL.json',checks)
 print('COEXEC_QUALIFIED',cid,flush=True);d.close()
c.drop(sharedbg);write(folder/'COMPLETE.json',dict(status='PASS',checks=len(checks)));print('COEXEC_QUALIFICATION_PASS',len(checks),flush=True)
