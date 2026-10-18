from deploy import *
from measure import conditioning
import sys,random
out=Path(sys.argv[1]);block=int(sys.argv[2]);bins=read(ROOT/'freeze/bins.json');cases=[c for c in read(INPUT/'plans/cases.json') if c['id'] in ['T01','T04','T06','T09','T12','T16']]
e=Engine();conditioning(e,out);e.close()
for c in cases:
 budget_check();start=time.perf_counter();e=Engine(mode=-1);d=Data(c['M'],c['N'],c['K'],ring=4,seed=290000+block*100+int(c['id'][1:]),workspace_words=max(workspace_for('SPLIT',c,bins),workspace_for('PC0_0',c,bins)));values=[];validation_s=0
 order=ACTIONS.copy();random.Random(3100+block+int(c['id'][1:])).shuffle(order)
 for action in order:
  jobs=[Job(e,d,slot=slot,**config(action,c,bins,e)) for slot in range(4)]
  for j in jobs:j.batch(2)
  result=[jobs[i%4].run() for i in range(8)];t=time.perf_counter();num=d.numerical(3);validation_s+=time.perf_counter()-t;values.append(dict(action=action,cpu_ready_us=float(np.mean([x[1] for x in result])),gpu_us=float(np.mean([x[0] for x in result])),numerical=num))
  for j in jobs:j.close()
 winner=min(values,key=lambda x:(x['cpu_ready_us'],ACTIONS.index(x['action'])))['action'];d.close();e.close();tune_us=(time.perf_counter()-start-validation_s)*1e6
 append(out/'tuner_pilots.jsonl',dict(case=c['id'],block=block,actions=values,order=order,winner=winner,init_tune_us=tune_us,scientific_validation_excluded_us=validation_s*1e6,requests_per_action=8,new_validation_input_seed=300000+block*100+int(c['id'][1:]),rule_hash_unchanged=sha(ROOT/'freeze/POLICY_FREEZE.json')))
 policies=['LIB_ALWAYS','SHAPE','RESOURCE','INIT_TUNE'];policies=policies[block%4:]+policies[:block%4]
 for policy in policies:
  records=[]
  for h in [1,32,256,4096]:
   p=BoundPlan(c,'LIB_ALWAYS' if policy=='INIT_TUNE' else policy,h,seed=300000+block*100+int(c['id'][1:]),action_override=winner if policy=='INIT_TUNE' else None)
   if h<=32:
    start_ns=time.time_ns();result=execute([p],[0]*h,0 if policy=='INIT_TUNE' else policy,h,dynamic=False);end_ns=time.time_ns();scope='MEASURED_COLD_H_REQUESTS';warm_us=0;total=result['total_completion_us']
   else:
    t=time.perf_counter();warm([p]);warm_us=(time.perf_counter()-t)*1e6;start_ns=time.time_ns();result=execute([p],[0]*64,0 if policy=='INIT_TUNE' else policy,h,dynamic=False);end_ns=time.time_ns();scope='ALGEBRAIC_H_TIMES_MEASURED_64_REQUEST_STEADY';total=h*result['cpu_ready_us']
   num=check_last([p],[0]*(h if h<=32 else 64));metadata=p.metadata();setup=metadata['setup_including_input_us']+(tune_us if policy=='INIT_TUNE' else 0)+warm_us
   samples=result.pop('samples');append(out/'lifecycle_samples.jsonl',dict(case=c['id'],block=block,policy=policy,H=h,start_ns=start_ns,end_ns=end_ns,samples=samples,timing_scope='C++ request durations; epoch interval also includes Python result decoding'));records.append(dict(H=h,action=p.action,setup_including_input_and_tuning_us=setup,plan_setup_excluding_input_us=metadata['plan_setup_excluding_input_us'],tuning_us=tune_us if policy=='INIT_TUNE' else 0,warmup_us=warm_us,request_result=result,total_lifecycle_us=setup+total,scope=scope,plan=metadata,correctness=num));p.close()
  append(out/'lifecycle.jsonl',dict(stage='S5_LIFECYCLE',case=c['id'],cohort='confirmation',block=block,policy=policy,records=records,profile_cost_scope='Device card and offline model fitting are cached here; additionally charged in fresh-device/model analysis, never claimed free',status='PASS'))
write(out/'complete.json',dict(status='PASS',block=block))
