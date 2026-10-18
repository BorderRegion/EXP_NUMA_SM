"""CPU-only descriptive diagnostics, cost accounting and evidence index. No fitting."""
from common import *
import numpy as np,collections,csv,sys,math
run=Path(sys.argv[1]) if len(sys.argv)>1 else runroot();dest=Path(sys.argv[2]) if len(sys.argv)>2 else ROOT/'derived'
phases=lines(dest/'phases.jsonl');valid=[x for x in phases if x['worker_status']=='COMPLETED'];choices=read(ROOT/'freeze/ALL_CHOICES_BEFORE_TEST.json');model=read(ROOT/'freeze/POLICY_FREEZE.json');card=read(ROOT/'freeze/RESOURCE_CARD.json');cases={c['id']:c for c in read(INPUT/'plans/cases.json')};ledger=lines(run/'ledger.jsonl')
def dump(name,value):write(dest/name,value)
def stats(values):
 a=np.array(values,dtype=float)
 return dict(n=len(a),min=float(a.min()),median=float(np.median(a)),mean=float(a.mean()),p95=float(np.quantile(a,.95)),max=float(a.max())) if len(a) else None
selection=[]
for cohort in ['development','confirmation','regression','ood_bypass']:
 for policy in ['BASE','SHAPE','RESOURCE','PERMUTED_RESOURCE']:
  rr=[x for x in choices if x['cohort']==cohort and x['policy']==policy]
  if rr:selection.append(dict(cohort=cohort,policy=policy,count=len(rr),actions=dict(collections.Counter(x['chosen_action'] for x in rr)),reorder_count=sum(x['chosen_action'].startswith('PC') for x in rr),reasons=dict(collections.Counter(x['reason'] for x in rr))))
dump('selection_summary.json',selection)
training=[]
for policy,rows in model['loso'].items():
 for action in ACTIONS:
  rr=[x for x in rows if x['action']==action]
  training.append(dict(policy=policy,action=action,shapes=len(rr),mae_us=float(np.mean([abs(x['predicted_us']-x['observed_us']) for x in rr])),rmse_us=float(np.sqrt(np.mean([(x['predicted_us']-x['observed_us'])**2 for x in rr]))),median_absolute_relative_error=float(np.median([abs(x['predicted_us']/x['observed_us']-1) for x in rr])),mean_absolute_log_error=float(np.mean([abs(np.log(x['predicted_us']/x['observed_us'])) for x in rr]))))
dump('loso_diagnostics.json',dict(scope='Whole-shape cross-validation prediction error, not deployment gain or a new threshold',rows=training,base_error_to_lib_us=model['base_error_to_lib_us'],paired_error_margin_us=model['paired_error_margin_us']))
from selection_math import choose_base,choose_plan
cv_decisions=[]
for cid in model['cases']:
 c=cases[cid];costs=model['action_setup_us_by_bin'][bin_id(c)];basepred={x['action']:x['predicted_us'] for x in model['loso']['SHAPE'] if x['case']==cid}
 base=choose_base(basepred,{a:max(0,costs[a]-costs['LIB']) for a in ACTIONS},model['base_error_to_lib_us']['SHAPE'],1024,model['selection_us'])
 for policy in ['SHAPE','RESOURCE']:
  rr=[x for x in model['loso'][policy] if x['case']==cid];pred={x['action']:x['predicted_us'] for x in rr};obs={x['action']:x['observed_us'] for x in rr};choice=choose_plan(pred,{a:max(0,costs[a]-costs[base]) for a in ACTIONS},model['paired_error_margin_us'][policy],1024,model['selection_us'],allowed_actions=ACTIONS,frozen_base_action=base);a=choice.chosen_action;best=min(ACTIONS,key=lambda k:obs[k])
  cv_decisions.append(dict(case=cid,policy=policy,base_action=base,chosen_action=a,observed_choice_us=obs[a],observed_LIB_us=obs['LIB'],observed_base_us=obs[base],observed_oracle_action=best,observed_oracle_us=obs[best],regret_us=obs[a]-obs[best],wrong_open=a.startswith('PC') and obs[a]>obs[base],wrong_open_loss_us=max(0,obs[a]-obs[base]) if a.startswith('PC') else 0,reason=choice.reason))
dump('loso_decision_diagnostics.json',dict(scope='Held-out-shape predictions with final global LOSO-derived guard and cached setup at H1024. Threshold calibration diagnostic, not nested-CV or independent confirmation.',rows=cv_decisions))
training_rows=read(ROOT/'freeze/TRAINING_ROWS.json');dev=[]
for cid in sorted({x['case_id'] for x in training_rows}):
 for action in ACTIONS:
  rr=[x for x in training_rows if x['case_id']==cid and x['action']==action]
  dev.append(dict(case=cid,shape=[cases[cid][k] for k in ['M','N','K']],action=action,n_blocks=len(rr),mean_cpu_us=float(np.mean([x['cpu_ready_us'] for x in rr])),block_cpu_us=[x['cpu_ready_us'] for x in rr],blocks=[x['source_block'] for x in rr],scope='Development calibration used for fitting; not confirmation'))
dump('development_action_table.json',dev)
formal=[]
for cid in sorted({x['case'] for x in valid if x['stage']=='S4_ACTION'}):
 for action in ACTIONS:
  rr=sorted([x for x in valid if x['stage']=='S4_ACTION' and x['case']==cid and x['action']==action and x['role']=='main'],key=lambda x:x['block'])
  if rr:formal.append(dict(case=cid,cohort=cases[cid]['split'],shape=[cases[cid][k] for k in ['M','N','K']],action=action,n_blocks=len(rr),cpu_us=float(np.mean([x['cpu_ready_us'] for x in rr])),gpu_us=float(np.mean([x['gpu_us'] for x in rr])),batch_us=float(np.mean([x['batch_per_replay_us'] for x in rr])),block_cpu_us=[x['cpu_ready_us'] for x in rr],block_gpu_us=[x['gpu_us'] for x in rr],blocks=[x['block'] for x in rr],recipe=rr[0]['recipe'],S=rr[0]['S']))
dump('formal_action_table.json',formal)
geometry_cost=[]
for r in formal:
 c=cases[r['case']];m,n,k=c['M'],c['N'],c['K'];action=r['action'];bm,bn=TILES[r['recipe']];tiles=math.ceil(m/bm)*math.ceil(n/bn);sample=next(x for x in valid if x['stage']=='S4_ACTION' and x['case']==r['case'] and x['action']==action and x['role']=='main');nodes=sample['actual_dag']['nodes'];prod=[x for x in nodes if x.get('function') in ['p0','p2','p3','n0','n2','n3','s0','s2','s3']];red=[x for x in nodes if x.get('function') in ['r','rn']]
 geometry_cost.append(dict(case=r['case'],cohort=r['cohort'],action=action,FLOPs=2*m*n*k,input_logical_bytes=2*k*(m+n),output_bytes=4*m*n,explicit_partial_valid_bytes=4*m*n*r['S'] if action not in ['LIB','SINGLE'] else 0,selected_explicit_workspace_bytes=(4*tiles*bm*bn*r['S'] if action.startswith('PC') else 4*m*n*r['S'] if action=='SPLIT' else 0),raw_harness_pool_bytes=sample['workspace_capacity_bytes'],output_tiles=None if action=='LIB' else tiles,producer_CTAs=None if action=='LIB' else sum(math.prod(x['grid']) for x in prod),reducer_CTAs=None if action=='LIB' else sum(math.prod(x['grid']) for x in red),tail_fraction=None if action=='LIB' else 1-m*n/(tiles*bm*bn),explicit_S=None if action=='LIB' else r['S'],library_internal_split='UNKNOWN' if action=='LIB' else 'NOT_LIBRARY',kernel_resource_declarations=nodes,scope='Logical bytes and observed launch geometry, not DRAM transactions or occupancy measurement; raw resident pool differs from selected partial allocation'))
dump('bottleneck_geometry.json',geometry_cost)
cardsum=[]
for rep in card['representatives']:
 samples=rep['samples'];chain=float(np.mean([x['matrix_us'] for x in samples]));p=float(np.mean([x['P_us'] for x in samples]));r=float(np.mean([x['R_us'] for x in samples]));delta=np.array([x['residual_us'] for x in samples]);cardsum.append(dict(case=rep['case'],shape=rep['shape'],P_span_mean_us=p,R_after_P_span_mean_us=r,uninstrumented_chain_mean_us=chain,R_over_chain_percent=100*r/chain,mean_absolute_interaction_fraction=float(np.mean(np.abs(delta))/chain),max_absolute_interaction_fraction=float(np.max(np.abs(delta))/chain),chain_us_all_cell_sample_range=[float(np.min([x['matrix_us'] for x in samples])),float(np.max([x['matrix_us'] for x in samples]))],scope='R/chain is diagnostic only, not all communication. Instrumented stage spans are measured separately; additive residual is not proven latency.'))
dump('resource_bottleneck_summary.json',cardsum)
regret=lines(dest/'regret.jsonl');regrets=[]
for cohort in ['confirmation','regression']:
 for policy in ['BASE','SHAPE','RESOURCE','PERMUTED_RESOURCE']:
  rr=[x for x in regret if x['cohort']==cohort and x['policy']==policy]
  if rr:regrets.append(dict(cohort=cohort,policy=policy,n_case_blocks=len(rr),wrong_open_count=sum(x['wrong_open'] for x in rr),wrong_open_loss_us=stats([x['wrong_open_loss_us'] for x in rr]),missed_PC_gain_us=stats([x['missed_PC_gain_us'] for x in rr]),missed_base_gain_us=stats([x['missed_base_gain_us'] for x in rr]),regret_us=stats([x['regret_us'] for x in rr]),worst_case_block=max(rr,key=lambda x:x['ratio_over_LIB'])))
dump('regret_summary.json',regrets)
# Whole-block interval on the noisy hindsight diagnostic envelope.
def bootstrap_ratios(rows,num,den):
 vals=[float(np.mean([np.log(x[num]/x[den]) for x in rows if x['block']==b])) for b in sorted({x['block'] for x in rows})];v=np.array(vals);result=dict(block_log_ratios=vals,gain_percent=float(100*(1-np.exp(v.mean()))),scope='Noisy retrospective zero-cost envelope; not deployable improvement')
 if len(v)>=3:
  rng=np.random.default_rng(20261017);b=v[rng.integers(len(v),size=(5000,len(v)))].mean(1);lo,hi=np.quantile(b,[.025,.975]);result['gain_percent_ci']=[float(100*(1-np.exp(hi))),float(100*(1-np.exp(lo)))];
 return result
oracle=lines(dest/'oracle_envelope.jsonl');envelope=[]
for cohort in ['confirmation','regression','M320_extrapolation','within_development_M']:
 rr=[x for x in oracle if (x['cohort']==cohort or (x['cohort']=='confirmation' and ((cohort=='M320_extrapolation' and cases[x['case']]['M']==320) or (cohort=='within_development_M' and cases[x['case']]['M']<=192))))]
 if rr:
  envelope.append(dict(cohort=cohort,case_blocks=len(rr),base_over_lib=bootstrap_ratios(rr,'base_oracle_us','LIB_us'),full_over_lib=bootstrap_ratios(rr,'full_oracle_us','LIB_us'),full_over_base=bootstrap_ratios(rr,'full_oracle_us','base_oracle_us'),base_winners=dict(collections.Counter(x['base_oracle_action'] for x in rr)),full_winners=dict(collections.Counter(x['full_oracle_action'] for x in rr))))
dump('oracle_summary.json',envelope)
# 1Hz worker telemetry and marked drift; no observations removed.
telemetry=[]
for folder in sorted((run/'raw').iterdir()):
 p=folder/'telemetry.csv'
 if not p.exists():continue
 rows=list(csv.DictReader(p.open()));item=dict(worker=folder.name,n_samples=len(rows))
 for k in ['temperature_c','power_mw','requested_limit_mw','enforced_limit_mw','sm_mhz','mem_mhz','gpu_util_pct']:
  item[k]=stats([float(x[k]) for x in rows if x.get(k,'').replace('.','',1).isdigit()])
 item['throttle_reasons_counts']=dict(collections.Counter(x.get('throttle_reasons') for x in rows));telemetry.append(item)
drift=lines(dest/'anchor_drift.jsonl');dump('state_and_drift.json',dict(telemetry=telemetry,anchor_drift_by_metric={metric:dict(n_pairs=len([x for x in drift if x['metric']==metric]),marked_over_5_percent=sum(x['over_5_percent'] for x in drift if x['metric']==metric),ratios=stats([x['end_over_begin'] for x in drift if x['metric']==metric])) for metric in ['cpu_ready_us','gpu_us','batch_per_replay_us']},scope='All anchors retained. Telemetry is 1 Hz worker observations; power cap is not fixed clock or per-kernel energy.'))
# Explicit calibration cost: measured experiment implementation, including its
# conditioning and scientific qualification. This is conservative, not a claim
# that an optimized deployment must spend this amount.
calibration_s=sum(x['worker_s'] for x in ledger if x['key'].startswith(('S2_base_','S2_action_')) or x['key']=='S2_setup')
freeze_pipeline_s=(datetime.datetime.fromisoformat(read(ROOT/'freeze/POLICY_FREEZE_HASHES.json')['frozen_at'])-datetime.datetime.fromisoformat(read(ROOT/'freeze/POLICY_MODEL_PROVISIONAL.json')['created_at'])).total_seconds()
build_name=Path(next(x['build'] for x in valid if x['stage']=='S4_ACTION')).name;host_build_s=read(ROOT/'build'/build_name/'build.json')['cpu_build_s']
shared=(calibration_s+model['cpu_fit_seconds']+freeze_pipeline_s+host_build_s)*1e6
card_us=sum(x['worker_s'] for x in ledger if x['key'].startswith('S2_card_'))*1e6
life=lines(dest/'lifecycle.jsonl');fresh=[]
for block in sorted({x['block'] for x in life if x['worker_status']=='COMPLETED'}):
 for h in [1,32,256,4096]:
  for policy in ['LIB_ALWAYS','SHAPE','RESOURCE','INIT_TUNE']:
   rr=[x for x in life if x['worker_status']=='COMPLETED' and x['block']==block and x['policy']==policy]
   if len(rr)!=6:continue
   records=[next(a for a in x['records'] if a['H']==h) for x in rr];cached=sum(x['total_lifecycle_us'] for x in records);offline=shared+(card_us if policy=='RESOURCE' else 0) if policy in ['SHAPE','RESOURCE'] else 0
   fresh.append(dict(block=block,H=h,policy=policy,n_signatures=6,cached_card_model_total_us=cached,additional_measured_offline_build_us=offline,fresh_total_us=cached+offline,request_scope=records[0]['scope']))
dump('fresh_model_lifecycle.json',dict(shared_measured_offline_build_us=shared,shared_cost_components_s=dict(action_calibration_workers=calibration_s,cpu_fit=model['cpu_fit_seconds'],rule_export_compile_verification_wall_interval=freeze_pipeline_s,final_host_adapter_compile=host_build_s),resource_card_worker_us=card_us,card_cpu_materialization_us=None,unmeasured='Card JSON CPU aggregation and complete cold deployment-process import are not separately timed. Rule export/compile/verification uses its observed wall interval, not isolated compiler CPU time; no complete cold-process claim.',scope='Six-signature model; one offline calibration/card charge per model, never six repeated charges. Actual conservative campaign implementation includes conditioning and scientific checks. Cached lifecycle includes real plan/input setup; H>=256 uses measured64 mean algebraically.',rows=fresh))
tuners=[];numerical=collections.defaultdict(list)
def visit(value):
 if isinstance(value,dict):
  for key,item in value.items():
   if key in ['relative_frobenius','max_scaled_error','fp64_subblock_max_scaled_error'] and isinstance(item,(float,int)):numerical[key].append(item)
   else:visit(item)
 elif isinstance(value,list):
  for item in value:visit(item)
for folder in sorted((run/'raw').iterdir()):
 tuners.extend(lines(folder/'tuner_pilots.jsonl'))
 for name in ['correctness.jsonl','qualifications.jsonl','lifecycle.jsonl']:
  for row in lines(folder/name):visit(row)
dump('numerical_summary.json',dict(metrics={k:stats(v) for k,v in numerical.items()},scope='All saved correctness records, including repeated validation/reference checks; count is not independent statistical replication. Limits remain in backend.py.'))
break_even=[]
for block in sorted({x['block'] for x in life if x['worker_status']=='COMPLETED'}):
 for cid in sorted({x['case'] for x in life}):
  lr=[x for x in life if x['worker_status']=='COMPLETED' and x['block']==block and x['case']==cid]
  if len(lr)!=4:continue
  base=next(y for x in lr if x['policy']=='LIB_ALWAYS' for y in x['records'] if y['H']==4096)
  for phase in lr:
   r=next(y for y in phase['records'] if y['H']==4096);saving=base['request_result']['cpu_ready_us']-r['request_result']['cpu_ready_us'];extra=r['setup_including_input_and_tuning_us']-base['setup_including_input_and_tuning_us'];break_even.append(dict(case=cid,block=block,policy=phase['policy'],action=r['action'],measured_steady_saving_us=saving,measured_extra_setup_us=extra,estimated_H=max(0,extra)/saving if saving>0 else None,scope='Exploratory algebraic extrapolation from H4096 plan and64 requests; assumes unchanged steady time, excludes fresh offline calibration; not a deployment decision'))
dump('init_tune_summary.json',dict(pilots=len(tuners),winner_counts=dict(collections.Counter(x['winner'] for x in tuners)),actual_tuning_cost_us=stats([x['init_tune_us'] for x in tuners]),break_even=break_even))
geometry=[]
for block,cid in sorted({(x['block'],x['case']) for x in valid if x['stage']=='S4_ACTION'}):
 rr=[x for x in valid if x['stage']=='S4_ACTION' and x['block']==block and x['case']==cid and x['action']=='LIB'];sigs=[sorted((n.get('function'),tuple(n.get('grid',[])),tuple(n.get('block',[])),n.get('shared_bytes')) for n in x['actual_dag']['nodes'] if n['type']==0) for x in rr]
 geometry.append(dict(block=block,case=cid,same_kernel_functions_and_geometry=all(s==sigs[0] for s in sigs),scope='Function/grid/block/shared-size equality across LIB beginning/main/end; does not establish fixed clocks or identical cache state'))
dump('anchor_geometry.json',geometry)
# Copy/submission/wait evidence comes from observed graphs and source, not guessed kernel counts.
plans=[]
for stage in ['S4_ACTION','S5_TRACE','S5_FFN','S5_OOD']:
 candidates=[x for x in valid if x['stage']==stage]
 seen=set()
 for row in candidates:
  pp=row.get('plans',[row])
  for p in pp:
   action=p.get('action');key=(action,p.get('second_action'))
   if key in seen:continue
   seen.add(key);plans.append(dict(stage=stage,phase_id=row['phase_id'],worker=row['worker'],action=action,second_action=p.get('second_action'),kernel_nodes=p.get('kernel_nodes'),body_nodes=p.get('body_nodes'),runtime_state=p.get('runtime_state'),workspace_bytes=p.get('workspace_bytes',row.get('workspace_capacity_bytes')),dag=p.get('actual_dag')))
profile_path=run/'raw'/worker_key('S6_profiles')/'profiles.json';profiles=read(profile_path) if profile_path.exists() else []
profile_summary=[]
for p in profiles:profile_summary.append(dict(label=p['label'],status=p['status'],kernel_count=len(p['kernel_events']),kernels=dict(collections.Counter(x['name'] for x in p['kernel_events'])),memcpy_count=len(p['memcpy_events']),cuda_api_counts=p['cuda_api_counts'],plan=p['plan'],scope=p['scope']))
dump('execution_evidence.json',dict(representative_actual_graphs=plans,profiles=profile_summary,submission='sr_run_async: one cuGraphLaunch of prepared body, no host sync; caller sr_wait at result boundary. sr_trace separately uses timed wrapper and one caller output-ready wait per request.',copies='No explicit intermediate memcpy in GEMM/PC/FFN graph. Inputs and host numerical references transfer outside measured request body. Verify actual graph nodes and CUPTI memcpy count.',raw_vs_lazy='S4 raw Engine(-1) holds10 Green and diagnostic module to compare all actions; lazy selected LIB only primary, no Green/enumeration/partial/diag, but cuBLAS has its own workspace.'))
deployment_cost=[]
for stage,cid,policy in sorted({(x['stage'],x['case'],x['policy'] if x['stage']!='S5_FFN' else 'CANONICAL_SHARED_ACTION_PAIR') for x in valid if x['stage'].startswith('S5_')}):
 rr=[x for x in valid if x['stage']==stage and x['case']==cid and (stage=='S5_FFN' or x['policy']==policy)]
 deployment_cost.append(dict(stage=stage,case=cid,policy=policy,n_blocks=len(rr),setup_including_input_us=stats([x['setup_us'] for x in rr]),plan_setup_excluding_input_us=stats([x['plan_setup_excluding_input_us'] for x in rr]),accounted_gpu_tensor_and_blas_bytes=stats([sum(p['gpu_tensor_bytes']+p['blas_workspace_bytes'] for p in x['plans']) for x in rr]),scope='Prepared signatures and four input slots per signature; explicit tensor/cuBLAS allocations counted, context/graph allocator overhead not individually measured'))
dump('deployment_costs.json',deployment_cost)
print('SUPPLEMENT_COMPLETE',len(formal),len(telemetry),len(fresh))
