from diag import *
from deploy import BoundPlan
import sys,hashlib
out=Path(sys.argv[1]);group=sys.argv[2]
eps=[x for x in read(INPUT/'plans/episodes.json') if x['process_group_id']==group]
cases={c['id']:c for c in read(PRIOR/'input/T10_SELECTIVE_REORDER_REPAIR_V2_20261017/plans/cases.json')}
ffn={c['id']:c for c in read(INPUT/'plans/focus_cases.json')['ffn']};bins=read(ROOT/'freeze/bins.json')
write(out/'process_anchor.json',host_state())
def seed_for(key):return 400000+int(hashlib.sha256(key.encode()).hexdigest()[:7],16)
def case_for(cid):return cases[cid] if cid not in ffn else {**cases[ffn[cid]['first_case']],'id':cid}
def make(cid,actions,identity,full=False):
 c=case_for(cid);t=time.perf_counter();e=Engine(mode=-1 if full else -2,diagnostic=False)
 d=Data(c['M'],c['N'],c['K'],ring=4,seed=seed_for(identity),chain=cid in ffn,workspace_words=max(workspace_for(a,c,bins) for a in actions))
 js={a:[Job(e,d,slot=s,**config(a,c,bins,e)) for s in range(4)] for a in actions}
 append(out/'setup.jsonl',dict(identity=identity,construction_us=(time.perf_counter()-t)*1e6,metadata={a:meta(v,e,d) for a,v in js.items()}))
 qualify(js,d,out,identity,'BEFORE');return e,d,js
def close(e,d,js,identity):
 qualify(js,d,out,identity,'AFTER',all_slots=False)
 for v in js.values():
  for j in v:j.close()
 d.close();e.close()
if group=='PILOT':
 pilots={}
 for cid in ['R_G017','R_G002','V14','V15','V16','F3','F4']:
  e,d,js=make(cid,['LIB'],'PILOT_'+cid)
  ep=dict(id='PILOT_'+cid,case=cid,block=-1,windows=1,order='A',conditioning='READY_RING4')
  r=episode(ep,js['LIB'],js['LIB'],8,out,seconds=0);t=r['windows_summary'][1]['mean_cpu_ready_us'];n=max(8,min(128,math.ceil(20000/t)));pilots[cid]=dict(n=n,lib_cpu_ready_us=t,source_id=ep['id']);close(e,d,js,cid)
 write(out/'PILOTS.json',dict(pilots=pilots,rule='clamp(ceil(20000/LIB-only CPU-ready mean of8 after8 warm requests),8,128)',status='FROZEN_BEFORE_FACTOR_RESULTS'))
else:
 pilot=read(ROOT/'freeze/PILOTS.json')['pilots']
 if eps[0]['kind'] in ['timer_scope','aa_factor','aa_single_slot','aa_independent']:
  cid=eps[0]['case'];full=eps[0]['fixture']=='ALL_ACTIONS_RESIDENT';e,d,js=make(cid,ACTIONS if full else ['LIB'],group,full)
  previous=None
  for ep in eps:
   ep={**ep,'windows':12,'previous_profile_in_process':previous};episode(ep,js['LIB'],js['LIB'],pilot[cid]['n'],out);previous=ep['conditioning']
   if ep.get('timer_mode')=='BODY_CPU_ONLY':
    check(lib.diag_body_once(js['LIB'][3].ptr));append(out/'correctness.jsonl',dict(identity=ep['id'],timer_mode='BODY_CPU_ONLY',numerical=d.numerical(3),body_matches_wrapped_child=True))
  close(e,d,js,group)
 else:
  # Preserve fixed plan order. Request traces sharing a case reuse the same data
  # pool across three policy entries, while plans/engines are built one at a time.
  i=0
  while i<len(eps):
   ep=eps[i];cid=ep['case'];budget_check()
   if ep['kind']!='trace':
    actions=['LIB'] if cid=='F3' else ['LIB','SINGLE'];e,d,js=make(cid,actions,ep['id'])
    ep={**ep,'conditioning':'READY_RING4'}
    # D4 finite F4 confirmation does the same recorded n-window warmups and
    # no additional 30s conditioner: reserved10min stage includes16 AA×30s.
    seconds=0 if ep['kind']=='ffn_independent' else 30
    episode(ep,js['LIB'],js.get('SINGLE',js['LIB']),pilot[cid]['n'],out,seconds=seconds);close(e,d,js,ep['id']);i+=1
   else:
    trace_eps=[]
    while i<len(eps) and eps[i]['kind']=='trace' and eps[i]['case']==cid:trace_eps.append(eps[i]);i+=1
    seq=read(INPUT/'plans/inherited_traces.json')['signatures'][cid];sigs=list(dict.fromkeys(seq));t=time.perf_counter()
    data={s:Data(cases[s]['M'],cases[s]['N'],cases[s]['K'],ring=4,seed=seed_for(group+'_'+cid+'_'+s)) for s in sigs}
    append(out/'setup.jsonl',dict(identity=group+'_'+cid,shared_input_pool_us=(time.perf_counter()-t)*1e6,signature_ids=sigs))
    for ep in trace_eps:
     dynamic=ep['policy']=='FROZEN_RESOURCE_DYNAMIC';policy='RESOURCE' if dynamic else 'BASE' if ep['policy']=='FROZEN_BASE_BOUND' else 'LIB_ALWAYS'
     plans=[BoundPlan(cases[s],policy,h=1024,existing_data=data[s],dynamic=dynamic) for s in sigs]
     expected={s:('SINGLE' if s in ['V14','V15','V16'] and policy!='LIB_ALWAYS' else 'LIB') for s in sigs}
     assert all(p.action==expected[p.c['id']] for p in plans)
     for p in plans:qualify({p.action:p.jobs},p.d,out,ep['id']+'_'+p.c['id'],'BEFORE')
     trace(ep,plans,seq,out,dynamic)
     for p in plans:
      slot=max(j for j,x in enumerate(seq) if x==p.c['id'])%4
      append(out/'correctness.jsonl',dict(identity=ep['id'],case=p.c['id'],slot=slot,when='ACTUAL_TRACE_LAST_OUTPUT',numerical=p.d.numerical(slot)))
      p.close()
    for d in data.values():d.close()
write(out/'complete.json',dict(status='PASS',group=group,episode_ids=[x['id'] for x in eps],end_host=host_state()))
