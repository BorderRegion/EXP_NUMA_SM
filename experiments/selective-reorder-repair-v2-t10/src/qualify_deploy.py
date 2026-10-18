from deploy import *
import sys
out=Path(sys.argv[1]);model=read(ROOT/'freeze/POLICY_FREEZE.json');rows=[]
for c in [dict(id='Q_tail',M=17,N=196,K=512),dict(id='Q_real',M=24,N=8192,K=16384)]:
 for policy in POLICIES[:4]:
  p=BoundPlan(c,policy,1024,seed=250001);before=p.e.state();check(lib.sr_run_async(p.jobs[0].ptr));check(lib.sr_wait(p.e.ptr));num=p.d.numerical(0);assert before==p.e.state();v=execute([p],[0]*8,policy,dynamic=True);checks=check_last([p],[0]*8);append(out/'qualifications.jsonl',dict(case=c,policy=policy,metadata=p.metadata(),numerical=num,result=v,checks=checks,async_state_unchanged=True));p.close()
for fc in read(INPUT/'plans/ffn_chains.json')[:1]:
 c=dict(id=fc['id'],M=fc['M'],N=fc['intermediate'],K=fc['hidden']);p=BoundPlan(c,'RESOURCE',1024,seed=250002,chain=True);v=execute([p],[0]*8,'RESOURCE',dynamic=False);append(out/'qualifications.jsonl',dict(case=c,policy='RESOURCE_FFN',metadata=p.metadata(),result=v,checks=check_last([p],[0]*8)));p.close()
write(out/'complete.json',dict(status='PASS'))
