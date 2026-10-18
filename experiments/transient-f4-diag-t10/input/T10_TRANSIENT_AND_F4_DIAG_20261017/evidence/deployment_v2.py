from deploy import *
from measure import conditioning
from policy_v2 import py_choice
import sys
out=Path(sys.argv[1]);mode=sys.argv[2];block=int(sys.argv[3]);case_map={c['id']:c for c in read(INPUT/'plans/cases.json')}
e=Engine();conditioning(e,out,seconds=30);e.close()
def save(identity,plans,ids,policy,dynamic,extra=None):
 budget_check()
 # Validate before the warmed measured interval; no checks between requests.
 for p in plans:
  for j in p.jobs:j.run();p.d.numerical(j.slot)
 warm(plans);start=time.time_ns();result=execute(plans,ids,policy,dynamic=dynamic);end=time.time_ns();checks=check_last(plans,ids);samples=result.pop('samples');metadata=[p.metadata() for p in plans]
 row=dict(**identity,**result,start_ns=start,end_ns=end,status='PASS',dynamic_rule_per_request=dynamic,plans=metadata,setup_us=sum(p.setup_us for p in plans),plan_setup_excluding_input_us=sum(p.plan_setup_excluding_input_us for p in plans),rule_sha256=sha(ROOT/'freeze/POLICY_FREEZE.json'),device_uuid=UUID,build=str(BUILD),evidence='ACTUAL_DEPLOYMENT',**(extra or {}))
 append(out/'phases.jsonl',row);append(out/'samples.jsonl',dict(phase_id=identity['phase_id'],samples=samples));append(out/'correctness.jsonl',dict(phase_id=identity['phase_id'],checks=checks));print(identity['phase_id'],round(result['total_completion_us']/1000,3),'ms',flush=True);return row
if mode in ['trace','binding','witness']:
 tr=read(INPUT/'plans/traces.json');traces=tr['signatures']
 if mode=='binding':traces={k:traces[k] for k in ['MIX_ALL16','BURST_ALL16']}
 if mode=='witness':
  w=read(ROOT/'freeze/witness.json');traces={'DISAGREEMENT_WITNESS':w['requests']} if w['requests'] else {}
 for tid,requests in traces.items():
  signatures=list(dict.fromkeys(requests));ids=[signatures.index(x) for x in requests];policies=POLICIES if mode=='trace' else ['RESOURCE_DYNAMIC','RESOURCE_BOUND'] if mode=='binding' else ['SHAPE','RESOURCE','PERMUTED_RESOURCE'];shift=block%len(policies);policies=policies[shift:]+policies[:shift]
  # One explicitly shared immutable input pool per trace/process. Selected
  # runtime/partial/graphs are newly built and charged for each policy.
  start=time.perf_counter();data={cid:Data(case_map[cid]['M'],case_map[cid]['N'],case_map[cid]['K'],ring=4,seed=310000+block*100+sum(map(ord,cid))) for cid in signatures};shared_us=(time.perf_counter()-start)*1e6
  append(out/'shared_input_pools.jsonl',dict(trace=tid,block=block,shared_input_us=shared_us,cases=signatures,bytes=sum(sum(x.numel()*x.element_size() for x in d.a+[d.b,d.c,d.d]) for d in data.values()),scope='Allocated once across sequential policies; fresh deployment must pay one copy, never five copies. No policy-specific resource or graph in shared pool.'))
  for policy in policies:
   use='RESOURCE' if policy.startswith('RESOURCE_') else policy;dynamic=policy!='RESOURCE_BOUND';binding_rule_dynamic=True if mode=='binding' else dynamic;plans=[BoundPlan(case_map[cid],use,1024,existing_data=data[cid],dynamic=binding_rule_dynamic) for cid in signatures]
   save(dict(phase_id=f'{block}_{tid}_{policy}',stage='S5_'+mode.upper(),block=block,case=tid,cohort='synthetic_request_trace',policy=policy,signature_ids=signatures,H=1024),plans,ids,use,dynamic,dict(binding_comparison_scope='Both entries bind the frozen dynamic-rule action; only per-request choice execution differs. AOT zero-steady-cost choices are separately frozen and used in FFN/lifecycle.' if mode=='binding' else None,shared_input_pool_us=shared_us,setup_fresh_including_shared_inputs_us=shared_us+sum(p.setup_us for p in plans)))
   for p in plans:p.close()
  for d in data.values():d.close()
elif mode=='ffn':
 for fc in read(INPUT/'plans/ffn.json'):
  c={**case_map[fc['first_case']],'id':fc['id']};policies=POLICIES[:4];policies=policies[block%4:]+policies[:block%4];seen={}
  for policy in policies:
   p=BoundPlan(c,policy,seed=320000+block*100+int(c['id'][1:]),chain=True,dynamic=False);key=(p.action,'LIB',json.dumps(p.jobs[0].dag,sort_keys=True))
   if key in seen:
    append(out/'aliases.jsonl',dict(stage='S5_FFN',block=block,case=c['id'],policy=policy,canonical_policy=seen[key],actions=key[:2],execution_dag_equal=True,plan=p.metadata(),setup_us=p.setup_us,scope='Identical static action pair/execution, canonical measured once; each policy initializer constructed and cost recorded independently.'));p.close();continue
   seen[key]=policy;save(dict(phase_id=f'{block}_{c["id"]}_{policy}',stage='S5_FFN',block=block,case=c['id'],cohort='synthetic_FFN',policy=policy,shape=c,H=1024),[p],[0]*64,policy,False);p.close()
elif mode=='ood':
 for c in [x for x in case_map.values() if x['split']=='ood_bypass']:
  policies=['LIB_ALWAYS','RESOURCE','SHAPE'];policies=policies[block%3:]+policies[:block%3]
  for policy in policies:
   p=BoundPlan(c,policy,seed=330000+block*100+int(c['id'][1:]),dynamic=True);assert p.action=='LIB';save(dict(phase_id=f'{block}_{c["id"]}_{policy}',stage='S5_OOD',block=block,case=c['id'],cohort='out_of_envelope',policy=policy,shape=c,H=1024),[p],[0]*32,policy,True);p.close()
else:raise ValueError(mode)
write(out/'complete.json',dict(status='PASS',mode=mode,block=block))
