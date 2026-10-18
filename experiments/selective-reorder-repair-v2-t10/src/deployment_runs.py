from deploy import *
from measure import conditioning
from policy_api import CPUChooser
import sys,random
out=Path(sys.argv[1]);mode=sys.argv[2];block=int(sys.argv[3]);case_map={c['id']:c for c in read(INPUT/'plans/cases.json')};chooser=CPUChooser()
e=Engine();conditioning(e,out);e.close()
def save(identity,plans,ids,policy,dynamic,warmup=True):
 budget_check()
 if warmup:warm(plans)
 start=time.time_ns();result=execute(plans,ids,policy,dynamic=dynamic);end=time.time_ns();checks=check_last(plans,ids);samples=result.pop('samples');metadata=[p.metadata() for p in plans];batch=None
 if len(plans)==1:
  v=plans[0].jobs[0].batch(max(8,len(ids)));batch=v[0]/max(8,len(ids))
 row=dict(**identity,**result,start_ns=start,end_ns=end,status='PASS',dynamic_rule_per_request=dynamic,plans=metadata,batch_per_replay_us=batch,setup_us=sum(p.setup_us for p in plans),plan_setup_excluding_input_us=sum(p.plan_setup_excluding_input_us for p in plans),rule_sha256=sha(ROOT/'freeze/POLICY_FREEZE.json'),device_uuid=UUID,build=str(BUILD))
 append(out/'phases.jsonl',row);append(out/'samples.jsonl',dict(phase_id=identity['phase_id'],samples=samples));append(out/'correctness.jsonl',dict(phase_id=identity['phase_id'],checks=checks))
 return row
if mode=='trace':
 plan=read(INPUT/'plans/dispatch_traces.json');traces=plan['traces']
 for tid,requests in traces.items():
  signatures=list(dict.fromkeys(requests));ids=[signatures.index(x) for x in requests];policies=POLICIES[:4]+(['PERMUTED_RESOURCE'] if tid in ['BURST','SHIFT_AND_FALLBACK'] else [])+['RESOURCE_BOUND'];shift=block%len(policies);policies=policies[shift:]+policies[:shift]
  for policy in policies:
   use='RESOURCE' if policy=='RESOURCE_BOUND' else policy;plans=[]
   for j,cid in enumerate(signatures):plans.append(BoundPlan(case_map[cid],use,plan['init_horizon_hint'],seed=260000+block*100+int(''.join(x for x in cid if x.isdigit()))))
   save(dict(phase_id=f'{block}_{tid}_{policy}',stage='S5_TRACE',block=block,case=tid,cohort='dispatch_stress',policy=policy,signature_ids=signatures,scope='Actual ordered total completion; synthetic multi-signature requests, not natural LLM distribution',H=plan['init_horizon_hint']),plans,ids,use,policy!='RESOURCE_BOUND')
   for p in plans:p.close()
elif mode=='ffn':
 for fc in read(INPUT/'plans/ffn_chains.json'):
  c=dict(id=fc['id'],M=fc['M'],N=fc['intermediate'],K=fc['hidden']);policies=POLICIES[:4];policies=policies[block%4:]+policies[:block%4];seen={}
  for policy in policies:
   first=chooser.choose(c,policy)['chosen_action'];second=chooser.choose(dict(M=c['M'],N=c['K'],K=c['N']),policy)['chosen_action'];key=(first,second)
   if key in seen:
    append(out/'aliases.jsonl',dict(stage='S5_FFN',block=block,case=c['id'],policy=policy,canonical_policy=seen[key],actions=key,scope='Same initialized action pair and static replay; selection/init costs are accounted separately in lifecycle.'));continue
   seen[key]=policy;p=BoundPlan(c,policy,seed=270000+block*100+int(c['id'][1:]),chain=True)
   save(dict(phase_id=f'{block}_{c["id"]}_{policy}',stage='S5_FFN',block=block,case=c['id'],cohort='LLM_SHAPED_CHAIN',policy=policy,shape=c,H=1024),[p],[0]*64,policy,False);p.close()
elif mode=='ood':
 for c in [x for x in case_map.values() if x['split']=='ood_bypass']:
  policies=['LIB_ALWAYS','RESOURCE','SHAPE'];policies=policies[block%3:]+policies[:block%3]
  for policy in policies:
   p=BoundPlan(c,policy,seed=280000+block*100+int(c['id'][1:]));assert p.action=='LIB';save(dict(phase_id=f'{block}_{c["id"]}_{policy}',stage='S5_OOD',block=block,case=c['id'],cohort='ood_bypass',policy=policy,shape=c,H=1024),[p],[0]*32,policy,True);p.close()
else:raise ValueError(mode)
write(out/'complete.json',dict(status='PASS',mode=mode,block=block))
