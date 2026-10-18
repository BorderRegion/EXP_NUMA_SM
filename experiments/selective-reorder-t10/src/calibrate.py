import os
from pathlib import Path
os.environ['PC_BUILD']=(Path(__file__).resolve().parents[1]/'freeze/CALIBRATION_BUILD.txt').read_text().strip()
from measure import *
import sys,random
out=Path(sys.argv[1]);mode=sys.argv[2];block=int(sys.argv[3]);cases=[c for c in read(INPUT/'plans/cases.json') if c['split']=='development']
e=Engine(mode=-2 if mode=='base' else -3 if mode=='card' else -1,diagnostic=mode!='base');conditioning(e,out)
if mode!='base':write(out/'roster.json',dict(groups=e.membership,quad=e.quad,halves=e.halves,state=e.state()))
bins=read(ROOT/'freeze/bins.json') if mode!='base' else None
if mode=='card':cases=[c for c in cases if c['id'] in read(INPUT/'plans/resource_representatives.json')['case_ids']]
for c in cases:
 budget_check();cid=c['id'];m,n,k=c['M'],c['N'],c['K'];words=workspace(c,3,8,True) if mode=='base' else max(workspace_for('SPLIT',c,bins),workspace_for('PC0_0',c,bins))
 d=Data(m,n,k,seed=170000+block*100+int(cid[1:]),ring=1 if mode=='card' else 4,s=8,workspace_words=words,workspace_slots=2 if mode=='card' else 1)
 if mode=='base':
  cnt=pilot(e,d,out,cid,cap=32);opts=[dict(kind=4 if s==1 else 0,recipe=r,s=s) for r in [0,2,3] for s in [1,2,4,8]]
  random.Random(1700+block+int(cid[1:])).shuffle(opts)
  opts=[dict(kind=3,s=1,recipe=0)]+opts[:6]+[dict(kind=3,s=1,recipe=0)]+opts[6:]+[dict(kind=3,s=1,recipe=0)]
  for idx,kw in enumerate(opts):
   action='LIB' if kw['kind']==3 else 'SINGLE' if kw['s']==1 else 'SPLIT'
   phase(e,d,out,dict(phase_id=f'{block}_{cid}_{idx}',stage='S2_BASE',block=block,case=cid,cohort='development',action=action,order=idx,role='anchor' if action=='LIB' else 'main'),kw,cnt)
 elif mode=='placement':
  cnt=pilot(e,d,out,cid,cap=32);opts=[a for a in ACTIONS if a!='SINGLE'];random.Random(1800+block+int(cid[1:])).shuffle(opts)
  # SAME SINGLE calibration is reused for both models from the two base blocks.
  # Do not describe noncontemporaneous calibration values as paired effects.
  b=bins[bin_id(c)];bits=[]
  for slot in range(d.ring):
   j=Job(e,d,slot=slot,**config('SPLIT',c,bins,e));j.run();d.numerical(slot);bits.append(d.d.cpu().view(torch.int32).clone());j.close()
  for idx,action in enumerate(opts):
   phase(e,d,out,dict(phase_id=f'{block}_{cid}_{action}',stage='S2_ACTION',block=block,case=cid,cohort='development',action=action,order=idx,role='main'),config(action,c,bins,e),cnt,check_bits=bits if action.startswith('PC') else None)
 else:
  opts=[(w,p,q) for w in range(2) for p in range(4) for q in range(4)];random.Random(1900+block+int(cid[1:])).shuffle(opts);b=bins[bin_id(c)]
  for idx,(w,p,q) in enumerate(opts):
   kw=dict(kind=2,recipe=b['split_recipe'],s=b['split_S'],slab=1,pg=[e.quad[p]]*2,cg=[e.quad[q]]*2,wslot=w)
   row=phase(e,d,out,dict(phase_id=f'{block}_{cid}_w{w}_{p}{q}',stage='S2_CARD',block=block,case=cid,cohort='development',action='CELL',P=p,C=q,W=w,order=idx,role='card'),kw,16,warm_ms=0)
   if w==0:
    j=Job(e,d,**kw,stages=1);j.batch(8);v=np.mean([j.run() for _ in range(4)],axis=0);append(out/'stages.jsonl',dict(case=cid,block=block,P=p,C=q,P_us=float(v[2]),R_us=float(v[3]),chain_us=float(v[0]),scope='SEPARATE_STAGE_INSTRUMENTED_REAL_PRODUCER_REDUCER'));j.close()
 d.close()
e.close();write(out/'complete.json',dict(status='PASS',mode=mode,block=block))
