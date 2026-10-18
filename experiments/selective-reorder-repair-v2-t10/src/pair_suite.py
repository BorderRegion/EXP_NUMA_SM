from paired import *
out=Path(sys.argv[1]);stage=sys.argv[2];block=int(sys.argv[3]);bins=read(ROOT/'freeze/bins.json');cases=read(INPUT/'plans/cases.json');orders=[x for x in read(INPUT/'plans/pair_orders.json') if x['stage']==stage and x['block']==block]
if stage=='EVALUATION' and (ROOT/'freeze/formal_scope.json').exists():
 keep=read(ROOT/'freeze/formal_scope.json')['case_ids'];orders=[x for x in orders if x['case_id'] in keep]
ids=list(dict.fromkeys(x['case_id'] for x in orders));
if stage=='EVALUATION':ids+= [cid for cid in ['V01','V06','V11','V16'] if cid not in ids]
ids=ids[block%len(ids):]+ids[:block%len(ids)];e=Engine(mode=-1,diagnostic=True);write(out/'roster.json',dict(groups=e.membership,quad=e.quad,halves=e.halves,state=e.state()))
for cid in ids:
 c=next(x for x in cases if x['id']==cid);budget_check();d=Data(c['M'],c['N'],c['K'],ring=4,seed=280000+block*1000+sum(map(ord,cid)),workspace_words=max(workspace_for('SPLIT',c,bins),workspace_for('PC0_0',c,bins)))
 jobs={a:[Job(e,d,slot=s,**config(a,c,bins,e)) for s in range(4)] for a in ACTIONS};qualify(jobs,d,cid,out,'BEFORE');meta={a:job_meta(js,e,d) for a,js in jobs.items()};write(out/f'graphs_{cid}.json',meta)
 n=pilot_ready(jobs['LIB'],out,cid);condition_jobs(jobs['LIB'],out,cid,30)
 identity=dict(case_id=cid,cohort=c['cohort'],block=block,stage=stage)
 if stage=='EVALUATION':
  frozen=[x for x in read(ROOT/'freeze/choices_before_timing.json') if x['case_id']==cid and x['dynamic']];write(out/f'decisions_{cid}.json',frozen)
  identity.update(decision_model_sha=sha(ROOT/'freeze/POLICY_FREEZE.json'),frozen_decisions_file=f'decisions_{cid}.json',chosen_action={x['policy']:x['chosen_action'] for x in frozen},base_action={x['policy']:x['base_action'] for x in frozen},prediction={x['policy']:x['log_predictions'] for x in frozen},horizon=1024,reason={x['policy']:x['reason'] for x in frozen},decision_scope='Frozen dynamic choices for action-table replay; raw candidate is independently timed, not the deployed chosen action. q/AA/setup for every action/base are in referenced per-case record.')
 pair(jobs['LIB'],jobs['LIB'],n,'ABBA' if block%2==0 else 'BAAB',dict(**identity,round=-1,quartet_id=f'{stage}_{block}_{cid}_AA_BEGIN',action='LIB',ref_action='LIB',anchor='BEGIN'),out,meta['LIB'],'anchors.jsonl')
 for q in [x for x in orders if x['case_id']==cid]:
  a,b=q['reference'],q['candidate'];pair(jobs[a],jobs[b],n,q['order'],dict(**identity,round=q['round'],quartet_id=q['id'],action=b,ref_action=a),out,dict(candidate=meta[b],reference=meta[a]))
 if stage=='EVALUATION':
  for q in [x for x in read(INPUT/'plans/pair_orders.json') if x['stage']=='PC_DIRECT' and x['block']==block and x['case_id']==cid]:
   a,b=q['reference'],q['candidate'];pair(jobs[a],jobs[b],n,q['order'],dict(**{**identity,'stage':'PC_DIRECT'},round=q['round'],quartet_id=q['id'],action=b,ref_action=a),out,dict(candidate=meta[b],reference=meta[a]),'pc_direct.jsonl')
 pair(jobs['LIB'],jobs['LIB'],n,'BAAB' if block%2==0 else 'ABBA',dict(**identity,round=-1,quartet_id=f'{stage}_{block}_{cid}_AA_END',action='LIB',ref_action='LIB',anchor='END'),out,meta['LIB'],'anchors.jsonl')
 qualify(jobs,d,cid,out,'AFTER')
 for js in jobs.values():
  for j in js:j.close()
 d.close();print(stage,block,cid,'PASS',n,flush=True)
e.close();write(out/'complete.json',dict(status='PASS',stage=stage,block=block,cases=ids,pairs=len(orders)))
