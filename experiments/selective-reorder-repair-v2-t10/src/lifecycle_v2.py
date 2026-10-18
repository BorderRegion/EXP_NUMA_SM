from deploy import *
from paired import windows,pilot_ready,condition_jobs,qualify,pair
import sys,random,math
out=Path(sys.argv[1]);block=int(sys.argv[2]);bins=read(ROOT/'freeze/bins.json');cases=[c for c in read(INPUT/'plans/cases.json') if c['id'] in ['V01','V04','V06','V09','V12','V16']]
for c in cases:
 budget_check();start=time.perf_counter();e=Engine(mode=-1);d=Data(c['M'],c['N'],c['K'],ring=4,seed=340000+block*100+int(c['id'][1:]),workspace_words=max(workspace_for('SPLIT',c,bins),workspace_for('PC0_0',c,bins)));jobs={a:[Job(e,d,slot=s,**config(a,c,bins,e)) for s in range(4)] for a in ACTIONS};build_end=time.perf_counter();tv=time.perf_counter();qualify(jobs,d,c['id'],out,'TUNER_BEFORE');validation_s=time.perf_counter()-tv;n=pilot_ready(jobs['LIB'],out,c['id']);tc=time.perf_counter();condition_jobs(jobs['LIB'],out,c['id'],30);conditioning_us=(time.perf_counter()-tc)*1e6
 actions=ACTIONS[1:];actions=actions[block:]+actions[:block];ratios={'LIB':0.};rows=[]
 for action in actions:
  zz=[]
  for rr in range(2):
   order='ABBA' if (block+rr+ACTIONS.index(action))%2==0 else 'BAAB';row=pair(jobs['LIB'],jobs[action],n,order,dict(case_id=c['id'],cohort='init_tune_only',block=block,round=rr,quartet_id=f'TUNE_{block}_{c["id"]}_{action}_{rr}',action=action,ref_action='LIB',stage='S5_INIT_TUNE'),out,filename='tuner_pairs.jsonl');rows.append(row);zz.append(row['log_ratio'])
  ratios[action]=float(np.mean(zz))
 winner=min(ACTIONS,key=lambda a:(ratios[a],ACTIONS.index(a)));tv=time.perf_counter();qualify(jobs,d,c['id'],out,'TUNER_AFTER');validation_s+=time.perf_counter()-tv
 for js in jobs.values():
  for j in js:j.close()
 d.close();e.close();tune_us=(time.perf_counter()-start-validation_s)*1e6
 append(out/'tuner_pilots.jsonl',dict(case=c['id'],block=block,log_ratios=ratios,winner=winner,init_tune_us=tune_us,scientific_validation_excluded_us=validation_s*1e6,conditioning_us=conditioning_us,init_graph_resource_input_us=(build_end-start)*1e6,requests_per_window=n,paired_rounds=2,selection='Min mean paired log ratio to current LIB; independent fresh inputs after selected-plan reconstruction',new_validation_input_seed=350000+block*100+int(c['id'][1:])))
 policies=['LIB_ALWAYS','SHAPE','RESOURCE','INIT_TUNE'];policies=policies[block%4:]+policies[:block%4]
 for policy in policies:
  records=[]
  for h in [1,32,1024,4096]:
   p=BoundPlan(c,'LIB_ALWAYS' if policy=='INIT_TUNE' else policy,h,seed=350000+block*100+int(c['id'][1:]),action_override=winner if policy=='INIT_TUNE' else None,dynamic=False)
   if h<=32:
    start_ns=time.time_ns();result=execute([p],[0]*h,0 if policy=='INIT_TUNE' else policy,h,dynamic=False);end_ns=time.time_ns();scope='MEASURED_COLD_H_REQUESTS';warm_us=0;total=result['total_completion_us']
   else:
    t=time.perf_counter();warm([p]);warm_us=(time.perf_counter()-t)*1e6;start_ns=time.time_ns();result=execute([p],[0]*64,0 if policy=='INIT_TUNE' else policy,h,dynamic=False);end_ns=time.time_ns();scope='ESTIMATED_H_TIMES_MEASURED_64_REQUEST_STEADY';total=h*result['cpu_ready_us']
   num=check_last([p],[0]*(h if h<=32 else 64));metadata=p.metadata();setup=metadata['setup_including_input_us']+(tune_us if policy=='INIT_TUNE' else 0)+warm_us;samples=result.pop('samples')
   append(out/'lifecycle_samples.jsonl',dict(case=c['id'],block=block,policy=policy,H=h,start_ns=start_ns,end_ns=end_ns,samples=samples));records.append(dict(H=h,action=p.action,setup_including_input_and_tuning_us=setup,plan_setup_excluding_input_us=metadata['plan_setup_excluding_input_us'],tuning_us=tune_us if policy=='INIT_TUNE' else 0,warmup_us=warm_us,request_result=result,total_lifecycle_us=setup+total,scope=scope,plan=metadata,correctness=num));p.close()
  append(out/'lifecycle.jsonl',dict(stage='S5_LIFECYCLE',case=c['id'],block=block,policy=policy,records=records,status='PASS',cost_scope='Cached device card/model here; fresh calibration/compile charged separately. Tuner includes its full implemented 30s conditioning; scientific numerical qualification excluded and reported.'))
 print('LIFECYCLE',block,c['id'],'PASS',flush=True)
write(out/'complete.json',dict(status='PASS',block=block))
