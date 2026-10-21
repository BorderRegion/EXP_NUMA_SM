from gqa_runtime import *
from micro_runtime import Micro
from measure import capture_ring
import os
folder=Path(os.environ['T10_WORKER_DIR']);c=Control();plan=read(RUN/'freeze/resource_sets.json');chosen=plan['blocks'][0]['placements'];groups=[('N19',0)]+[('E56',c.create(list(range(56))))]+[(p['name'],c.create(p['foreground_sm_ids'])) for p in chosen]
checks=[];micro_pilot={};gqa_pilot={}
for recipe in ['HOT2_DEFAULT','HOT2_CG','STREAM32_DEFAULT','STREAM32_CG','STREAM128_CG','REG_FMA']:
 for grid in [40,160]:
  d=Micro(recipe,grid,190000000+grid);ptr=[]
  for name,g in [groups[1],groups[2],groups[-1]]:
   graphs,_=capture_ring(c,g,d,1);t=c.run(graphs,4)
   for slot in range(4):c.run([graphs[slot]],1);checks.append(dict(type='micro',recipe=recipe,grid=grid,policy=name,slot=slot,**d.check(slot)))
   if name=='E56':micro_pilot[recipe+'_'+str(grid)]=dict(gpu_us=float(np.median(t[:,0])),batch=max(1,min(32,2**int(np.clip(np.floor(np.log2(500/max(np.median(t[:,0]),1))),0,5)))))
   c.graph_drop(graphs)
  del d
  torch.cuda.empty_cache()
for case0 in read(RUN/'freeze/experiment_plan.json')['gqa_cases']:
 case=dict(id=case0['id'],B=case0['B'],H=case0['Hq'],HK=case0['Hkv'],D=case0['D'],L=max(case0['lengths']),lengths=case0['lengths'])
 d=GQAData(case,190100000+case['H']+case['L'],0)
 for append in [False,True]:
  n19_outputs={}
  for name,g in groups:
   d.reset();j=GQAJob(d,append,'N19' if name=='N19' else 'E56');graphs,_=capture_ring(c,g,j,1);t=c.run(graphs,4)
   for slot in range(4):
    c.run([graphs[slot]],1)
    if name=='N19':n19_outputs[slot]=d.out.cpu().clone()
    q=d.check_mode(append,slot,n19_outputs[slot]);checks.append(dict(type='gqa',case=case['id'],append=append,policy=name,slot=slot,**q))
    if j.mode==0 and not j.fused:assert q['same_input_N19_raw_bit_equal'],q
   if name=='N19':gqa_pilot[case['id']+'_'+str(int(append))]=dict(gpu_us=float(np.median(t[:,0])),batch=max(1,min(16,2**int(np.clip(np.floor(np.log2(500/max(np.median(t[:,0]),1))),0,4)))))
   c.graph_drop(graphs)
   write(folder/'NUMERICAL.json',checks)
  print('QUALIFIED_GQA',case['id'],append,flush=True)
 d.close()
# Explicit paged-tail checks use the same body/config, changing lengths only for qualification.
for G,L in [(4,31),(8,63)]:
 case=dict(id='GQA4_SHORT' if G==4 else 'GQA8_LONG',B=1,H=G*2,HK=2,D=128,L=L,lengths=[L])
 d=GQAData(case,190110000+L,0)
 for name,g in [groups[0],groups[2],groups[-1]]:
  d.reset();j=GQAJob(d,True,'N19' if name=='N19' else 'E56');graphs,_=capture_ring(c,g,j,1)
  for slot in range(4):c.run([graphs[slot]],1);checks.append(dict(type='gqa_tail',case=case['id'],length=L,policy=name,slot=slot,**d.check_mode(True,slot)))
  c.graph_drop(graphs)
 d.close()
write(folder/'NUMERICAL.json',checks);write(RUN/'freeze/PILOT_BATCH.json',dict(micro=micro_pilot,gqa=gqa_pilot,source='All-resource native-only pilots, prior to placement performance; same counts shared by policies'))
for _,g in groups[1:]:c.drop(g)
write(folder/'COMPLETE.json',dict(status='PASS',checks=len(checks)));print('OPS_QUALIFICATION_PASS',len(checks),flush=True)
