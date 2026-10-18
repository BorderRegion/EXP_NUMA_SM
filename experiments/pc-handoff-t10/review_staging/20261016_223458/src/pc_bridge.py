from measure import *
assert (ROOT/'freeze/production_implementation.json').exists(), 'Production qualification must precede bridge/formal measurements'
import sys,random
out=Path(sys.argv[1]);block=int(sys.argv[2]);selection=json.loads((ROOT/'freeze/selection.json').read_text());rule=json.loads((ROOT/'freeze/pc_rule.json').read_text());e=Engine(mode=rule['partition']);groups=e.halves[rule['partition']];assert [e.membership[g] for g in groups]==rule['actual_SM_sets'];write(out/'environment.json',dict(membership=e.membership,groups=groups,init_ms=e.init_ms,roster_ms=e.roster_ms,setup_costs=e.setup_costs));conditioning(e,out)
for c in selection['representatives']:
 cid=c['case_id'];d=Data(c['M'],c['N'],c['K'],s=c['S'],seed=40000+block*100+int(cid[1:]),ring=2);r=c['recipe'];s=c['S'];bits=qualification(e,d,dict(recipe=r,s=s,kind=0),out,cid)
 phase(out,e,d,dict(phase_id=f'{block}_{cid}_LIB',stage='E2_BRIDGE',block=block,case=cid,policy='LIB'),dict(recipe=r,s=s,kind=3),requests=64,replays=256)
 policies=[('G',0),('M',rule['pi']),('P',1-rule['pi'])];seen={}
 for label,pi in policies:
  if pi in seen:append(out/'aliases.jsonl',dict(case=cid,policy=label,alias=seen[pi],reason='Identical frozen implementation and parameters'));continue
  seen[pi]=label;cg=groups[::-1] if pi else groups
  for slab in [1]:
   phase(out,e,d,dict(phase_id=f'{block}_{cid}_{label}_layout{slab}',stage='E2_BRIDGE',block=block,case=cid,policy=label,pi=pi),dict(recipe=r,s=s,kind=1,slab=slab,pg=groups,cg=cg),requests=64,replays=256,check_bitwise=bits)
  j=Job(e,d,recipe=r,s=s,kind=1,slab=1,pg=groups,cg=cg,diag=1,generation=51+block);append(out/'placement.jsonl',dict(case=cid,policy=label,check=j.placement()));j.close()
 # Six prespecified conditions, all use the same four-node layout and fixed PC pairing.
 cg=groups[::-1] if rule['pi'] else groups
 conditions=[('NATURAL',{}),('REVERSE_C',dict(cg=cg[::-1])),('OTHER_WORKSPACE',dict(wslot=1)),('SCRATCH',dict(scratch=1)),('REVERSE_TASKS',dict(task_reverse=1)),('REVERSE_SUBMIT',dict(submit_reverse=1))]
 random.Random(block+9).shuffle(conditions)
 for label,change in conditions:
  kw=dict(recipe=r,s=s,kind=1,slab=1,pg=groups,cg=cg);kw.update(change)
  phase(out,e,d,dict(phase_id=f'{block}_{cid}_cf_{label}',stage='E2_COUNTERFACTUAL',block=block,case=cid,policy=label),kw,requests=64,replays=256,check_bitwise=bits)
  if label in ['NATURAL','SCRATCH']:
   j=Job(e,d,**kw,stages=1);[j.run() for _ in range(8)];a=[j.run() for _ in range(32)];j.close();append(out/'scratch_stages.jsonl',dict(case=cid,block=block,condition=label,chain_us=float(np.mean([x[0] for x in a])),P_us=float(np.mean([x[2] for x in a])),R_us=float(np.mean([x[3] for x in a])),scratch_us=float(np.mean([x[4] for x in a])) if label=='SCRATCH' else None,chain_less_measured_scratch_us=float(np.mean([x[0]-x[4] for x in a])) if label=='SCRATCH' else float(np.mean([x[0] for x in a])),note='Separate instrumented spans; scratch is a cache intervention, not a guaranteed flush.'))
 print('BRIDGE_CASE_COMPLETE',block,cid,flush=True);d.close()
e.close();write(out/'complete.json',dict(status='PASS'))
