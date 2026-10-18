from measure import *
from policy_api import CPUChooser,POLICIES
import sys
out=Path(sys.argv[1]);block=int(sys.argv[2]);bins=read(ROOT/'freeze/bins.json');chooser=CPUChooser();cases=[c for c in read(INPUT/'plans/cases.json') if c['split'] in ['confirmation','regression']];orders=read(INPUT/'plans/formal_orders.json')['orders']
if elapsed()>240*60:
 allowed=['T01','T03','T05','T07','T09','T11','T13','T15','R_G002','R_G008','R_G017','R_G039']
 # This branch is frozen once before block0; all subsequent blocks share it.
 if block==0:write(ROOT/'freeze/FORMAL_COVERAGE.json',dict(case_ids=allowed,reason='PREDECLARED_TIME_BUDGET_REDUCTION'))
if not (ROOT/'freeze/FORMAL_COVERAGE.json').exists():write(ROOT/'freeze/FORMAL_COVERAGE.json',dict(case_ids=[c['id'] for c in cases],reason='FULL_FIXED_MATRIX'))
coverage=read(ROOT/'freeze/FORMAL_COVERAGE.json');cases=[c for c in cases if c['id'] in coverage['case_ids']];e=Engine(mode=-1,diagnostic=True);conditioning(e,out);write(out/'roster.json',dict(groups=e.membership,quad=e.quad,halves=e.halves))
for c in cases:
 cid=c['id'];choices={policy:chooser.choose(c,policy,1024) for policy in POLICIES};append(out/'choices_before_measurement.jsonl',dict(at=utc(),case=cid,block=block,cohort=c['split'],choices=choices,rule_sha256=sha(ROOT/'freeze/POLICY_FREEZE.json')))
 d=Data(c['M'],c['N'],c['K'],ring=4,seed=230000+block*100+int(''.join(x for x in cid if x.isdigit())),workspace_words=max(workspace_for('SPLIT',c,bins),workspace_for('PC0_0',c,bins)));cnt=pilot(e,d,out,cid,128);bits=[]
 for slot in range(4):
  j=Job(e,d,slot=slot,**config('SPLIT',c,bins,e));j.run();d.numerical(slot);bits.append(d.d.cpu().view(torch.int32).clone());j.close()
 order=next(x for x in orders if x['case_id']==cid and x['block']==block);items=[('LIB','begin')]+[(a,'main') for a in order['main_order']]+[('LIB','end')]
 for idx,(action,role) in enumerate(items):phase(e,d,out,dict(phase_id=f'{block}_{cid}_{idx}_{action}',stage='S4_ACTION',block=block,case=cid,cohort=c['split'],action=action,role=role,order=idx,planned_row=order['row_of_18'],rule_sha256=sha(ROOT/'freeze/POLICY_FREEZE.json')),config(action,c,bins,e),cnt,check_bits=bits if action.startswith('PC') else None)
 d.close()
e.close();write(out/'complete.json',dict(status='PASS',block=block,cases=len(cases)))
