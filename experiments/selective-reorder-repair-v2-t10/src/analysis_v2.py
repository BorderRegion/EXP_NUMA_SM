"""CPU-only analysis of all settled raw attempts. No filtering by performance."""
from common import *
import sys,math,collections,numpy as np
sys.path.insert(0,str(ROOT/'reference'))
from paired_stats import block_bootstrap_logratios,quartet_contrast,quantile
from policy_v2 import py_choice,POLICIES
R=runroot();D=R/'derived';D.mkdir(exist_ok=True)
def gather(pattern,name):
 return [r for p in sorted((R/'raw').glob(pattern)) for r in lines(p/name)]
def ci(vals,conf=.95):
 if len(vals)<2:return dict(status='INSUFFICIENT_INDEPENDENT_BLOCKS',n=len(vals),values=vals)
 x=block_bootstrap_logratios(vals,conf);return dict(**x,time_reduction_pct=100*(1-x['ratio']),time_reduction_ci_pct=[100*(1-x['ci'][1]),100*(1-x['ci'][0])],block_log_ratios=vals)
aa_records=gather('S1_aa_*','aa.jsonl');noise=[]
for history in ['CLEAN','CHECK_GAP','IDLE_MATCHED']:
 rr=[x for x in aa_records if x['history']==history];z=[v['log_ratio'] for r in rr for v in r['contrasts']];blocks=[float(np.mean([v['log_ratio'] for r in rr if r['block']==b for v in r['contrasts']])) for b in sorted(set(r['block'] for r in rr))]
 noise.append(dict(history=history,episodes=len(rr),quartets=len(z),abs_log_median=float(np.median(np.abs(z))) if z else None,abs_log_q90=float(np.quantile(np.abs(z),.9)) if z else None,ratio_range=[math.exp(min(z)),math.exp(max(z))] if z else None,more_than_1pct=sum(abs(math.exp(x)-1)>.01 for x in z),more_than_5pct=sum(abs(math.exp(x)-1)>.05 for x in z),signed=ci(blocks),scope='Three quartets/episode; only two independent process blocks. No equivalence claim.'))
write(D/'noise_summary.json',noise)
pairs=gather('S4_*','pairs.jsonl');direct=gather('S4_*','pc_direct.jsonl');anchors=gather('S4_*','anchors.jsonl');cases={x['id']:x for x in read(INPUT/'plans/cases.json')};choice=read(ROOT/'freeze/choices_before_timing.json') if (ROOT/'freeze/choices_before_timing.json').exists() else []
block_tables=[]
for cid,b in sorted(set((x['case_id'],x['block']) for x in pairs)):
 rr=[x for x in pairs if x['case_id']==cid and x['block']==b];obs={'LIB':0.};gpu={'LIB':0.}
 for a in ACTIONS[1:]:
  zz=[x for x in rr if x['action']==a]
  if len(zz)==2:obs[a]=float(np.mean([x['log_ratio'] for x in zz]));gpu[a]=float(np.mean([x['gpu']['log_ratio'] for x in zz]))
 if len(obs)!=9:continue
 libt=math.exp(float(np.mean([math.log(x['reference_geomean_us']) for x in rr])));block_tables.append(dict(case_id=cid,block=b,cohort=cases[cid]['cohort'],M=cases[cid]['M'],logs=obs,gpu_logs=gpu,lib_us=libt,paired_reference='Each action has its own contemporaneous LIB quartet; normalized action-to-action comparisons share a modeled normalization, not a direct same quartet.'))
write(D/'action_block_table.json',block_tables)
comparison=[];opportunity=[];diagnostics=[]
for cohort,pred in [('new_confirmation',lambda x:x['cohort']=='new_confirmation'),('M224_extrapolation',lambda x:x['cohort']=='new_confirmation' and x['M']==224),('regression',lambda x:x['cohort']=='regression')]:
 table=[x for x in block_tables if pred(x)];bs=sorted(set(x['block'] for x in table));ids=sorted(set(x['case_id'] for x in table))
 if not table:continue
 for dyn in [False,True]:
  chosen={(x['case_id'],x['policy']):x['chosen_action'] for x in choice if x['dynamic']==dyn}
  for a,b in [('RESOURCE','SHAPE'),('RESOURCE','LIB_ALWAYS'),('BASE','LIB_ALWAYS'),('SHAPE','BASE'),('RESOURCE','BASE'),('RESOURCE','PERMUTED_RESOURCE')]:
   vals=[float(np.mean([x['logs'][chosen[x['case_id'],a]]-x['logs'][chosen[x['case_id'],b]] for x in table if x['block']==bl])) for bl in bs]
   comparison.append(dict(cohort=cohort,policies=[a,b],dynamic=dyn,n_shapes=len(ids),structural_alias=all(chosen[c,a]==chosen[c,b] for c in ids),evidence='ACTION_TABLE_REPLAY',**ci(vals,.975 if cohort=='new_confirmation' and (a,b) in [('RESOURCE','SHAPE'),('RESOURCE','LIB_ALWAYS')] else .95)))
  for cid in ids:
   rr=[x for x in table if x['case_id']==cid];mean={a:float(np.mean([x['logs'][a] for x in rr])) for a in ACTIONS};best=min(ACTIONS,key=lambda a:mean[a]);basebest=min(ACTIONS[:3],key=lambda a:mean[a])
   for p in POLICIES[1:]:
    dd=next(x for x in choice if x['case_id']==cid and x['policy']==p and x['dynamic']==dyn);a=dd['chosen_action'];base=dd['base_action'];loss=math.exp(mean[a])-math.exp(mean[best]);libus=float(np.mean([x['lib_us'] for x in rr]));observed=ci([x['logs'][a]-x['logs'][base] for x in rr]);vs_lib=ci([x['logs'][a] for x in rr]);diagnostics.append(dict(cohort=cohort,case_id=cid,policy=p,dynamic=dyn,chosen=a,base=base,raw_argmin=dd['raw_argmin'],hindsight_best=best,hindsight_base_best=basebest,regret_normalized_to_LIB=loss,regret_us=loss*libus,pc_open=a.startswith('PC'),observed_chosen_vs_base=observed,observed_chosen_vs_LIB=vs_lib,non_native_slower_than_LIB_point_estimate=a!='LIB' and mean[a]>0,non_native_slower_than_LIB_CI=a!='LIB' and vs_lib.get('time_reduction_ci_pct',[0,0])[1]<0,pc_slower_than_base_CI=a.startswith('PC') and observed.get('time_reduction_ci_pct',[0,0])[1]<0,false_open_point_estimate=a.startswith('PC') and mean[a]>mean[base],false_closed_point_estimate=not a.startswith('PC') and mean[best]<mean[base] and best.startswith('PC'),scope='Errors versus noisy retrospective means are diagnostics, not ground-truth winner labels.'))
 # Cross-block oracle: choose action using other five blocks then evaluate held block.
 for pool,label in [(ACTIONS[:3],'BASE_POOL'),(ACTIONS,'FULL_POOL')]:
  vals=[];selections=[]
  for bl in bs:
   logs=[]
   for cid in ids:
    train=[x for x in table if x['case_id']==cid and x['block']!=bl];test=next(x for x in table if x['case_id']==cid and x['block']==bl)
    win=min(pool,key=lambda a:float(np.mean([x['logs'][a] for x in train])));logs.append(test['logs'][win]);selections.append(dict(held_block=bl,case_id=cid,chosen=win,held_log_ratio=test['logs'][win]))
   vals.append(float(np.mean(logs)))
  opportunity.append(dict(cohort=cohort,pool=label,scope='LEAVE_ONE_PROCESS_BLOCK_OUT_FREE_SEARCH_REFERENCE_NOT_DEPLOYED',n_shapes=len(ids),selections=selections,**ci(vals)))
for cohort in ['new_confirmation','M224_extrapolation','regression']:
 base=next((x for x in opportunity if x['cohort']==cohort and x['pool']=='BASE_POOL'),None);full=next((x for x in opportunity if x['cohort']==cohort and x['pool']=='FULL_POOL'),None)
 if base and full:opportunity.append(dict(cohort=cohort,pool='FULL_VS_BASE_INCREMENT',scope='CROSS_BLOCK_FREE_SEARCH_INCREMENT_NOT_DEPLOYED',n_shapes=base['n_shapes'],**ci([a-b for a,b in zip(full['block_log_ratios'],base['block_log_ratios'])])))
write(D/'method_action_replay.json',comparison);write(D/'prediction_errors.json',diagnostics);write(D/'oracle_cross_block.json',opportunity)
dirs=[]
for cid,part in sorted(set((x['case_id'],int(x['action'][2])) for x in direct)):
 rr=[x for x in direct if x['case_id']==cid and int(x['action'][2])==part];bs=sorted(set(x['block'] for x in rr));vals=[float(np.mean([x['log_ratio'] for x in rr if x['block']==b])) for b in bs];dirs.append(dict(case_id=cid,partition=part,comparison='OPPOSITE / SAME',quartets=len(rr),**ci(vals)))
write(D/'pc_direct.json',dirs)
if anchors:
 write(D/'formal_noise.json',dict(quartets=len(anchors),cpu_ratio_range=[min(x['ratio'] for x in anchors),max(x['ratio'] for x in anchors)],gpu_ratio_range=[min(x['gpu']['ratio'] for x in anchors),max(x['gpu']['ratio'] for x in anchors)],gpu_more_than_5pct=sum(abs(x['gpu']['ratio']-1)>.05 for x in anchors),worst_witnesses=[dict(quartet_id=x['quartet_id'],cpu_ratio=x['ratio'],gpu_ratio=x['gpu']['ratio'],windows=[{k:w[k] for k in ['label','n','mean_cpu_us','mean_gpu_us','wall_start_ns','wall_end_ns']} for w in x['windows']]) for x in sorted(anchors,key=lambda z:abs(z['log_ratio']),reverse=True)[:4]],absolute_log_q90=float(np.quantile([abs(x['log_ratio']) for x in anchors],.9)),more_than_1pct=sum(abs(x['ratio']-1)>.01 for x in anchors),more_than_5pct=sum(abs(x['ratio']-1)>.05 for x in anchors),all_retained=True,by_case=[dict(case_id=cid,ratios=[x['ratio'] for x in anchors if x['case_id']==cid]) for cid in sorted(set(x['case_id'] for x in anchors))]))
phases=gather('S5_*','phases.jsonl');aliases=gather('S5_*','aliases.jsonl');actual=[]
for stage in sorted(set(x['stage'] for x in phases)):
 rr=[x for x in phases if x['stage']==stage];bs=sorted(set(x['block'] for x in rr));pp=sorted(set(x['policy'] for x in rr));comparisons=[('RESOURCE','SHAPE'),('RESOURCE','LIB_ALWAYS'),('BASE','LIB_ALWAYS'),('SHAPE','LIB_ALWAYS'),('RESOURCE','BASE'),('RESOURCE','PERMUTED_RESOURCE')]
 if stage=='S5_BINDING':comparisons=[('RESOURCE_BOUND','RESOURCE_DYNAMIC')]
 # FFN aliases refer to canonical actual timing, never fabricated independent runs.
 table={(x['block'],x['case'],x['policy']):x for x in rr}
 if stage=='S5_FFN':
  for a in aliases:table[a['block'],a['case'],a['policy']]=table[a['block'],a['case'],a['canonical_policy']]
 for a,b in comparisons:
  vals=[];totals=[];worst=[]
  for bl in bs:
   cs=sorted(set(k[1] for k in table if k[0]==bl and (bl,k[1],a) in table and (bl,k[1],b) in table))
   if not cs:continue
   ta=sum(table[bl,c,a]['total_completion_us'] for c in cs);tb=sum(table[bl,c,b]['total_completion_us'] for c in cs);vals.append(math.log(ta/tb));totals.append(dict(block=bl,cases=cs,candidate_total_us=ta,reference_total_us=tb))
   worst.extend([dict(block=bl,case=c,ratio=table[bl,c,a]['total_completion_us']/table[bl,c,b]['total_completion_us']) for c in cs])
  if vals:actual.append(dict(stage=stage,policies=[a,b],evidence='ACTUAL_DEPLOYMENT',metric='SUM_ACTUAL_COMPLETION_TIME_PER_BLOCK',totals=totals,worst_phase=max(worst,key=lambda x:x['ratio']),**ci(vals,.975 if stage=='S5_TRACE' and (a,b) in [('RESOURCE','SHAPE'),('RESOURCE','LIB_ALWAYS')] else .95)))
write(D/'actual_comparisons.json',actual)
per_trace=[]
tr=[x for x in phases if x['stage']=='S5_TRACE']
for tid in sorted(set(x['case'] for x in tr)):
 for a,b in [('RESOURCE','SHAPE'),('RESOURCE','LIB_ALWAYS'),('BASE','LIB_ALWAYS')]:
  blocks=[];values=[];gpu_values=[]
  for bl in sorted(set(x['block'] for x in tr)):
   aa=next((x for x in tr if x['case']==tid and x['block']==bl and x['policy']==a),None);bb=next((x for x in tr if x['case']==tid and x['block']==bl and x['policy']==b),None)
   if aa is None or bb is None:continue
   values.append(math.log(aa['total_completion_us']/bb['total_completion_us']));gpu_values.append(math.log((aa['gpu_us']*aa['requests'])/(bb['gpu_us']*bb['requests'])));blocks.append(dict(block=bl,candidate_total_us=aa['total_completion_us'],reference_total_us=bb['total_completion_us'],candidate_gpu_span_sum_us=aa['gpu_us']*aa['requests'],reference_gpu_span_sum_us=bb['gpu_us']*bb['requests']))
  if values:per_trace.append(dict(trace=tid,policies=[a,b],totals=blocks,gpu_span_diagnostic=ci(gpu_values),scope='POSTHOC_EXPLORATORY_PER_PREDECLARED_TRACE; added during S5 block3 after observing sequence differences. No changes to primary pooled comparison, frozen choices or measurements. GPU span sum is not total wall time.',**ci(values)))
write(D/'per_trace_comparisons.json',per_trace)
paid=[];tr=[x for x in phases if x['stage']=='S5_TRACE']
for a,b in [('RESOURCE','SHAPE'),('RESOURCE','LIB_ALWAYS'),('BASE','LIB_ALWAYS')]:
 vals=[];totals=[]
 for bl in sorted(set(x['block'] for x in tr)):
  aa=[x for x in tr if x['block']==bl and x['policy']==a];bb=[x for x in tr if x['block']==bl and x['policy']==b]
  if len(aa)!=3 or len(bb)!=3:continue
  ta=sum(x['total_completion_us']+x['setup_fresh_including_shared_inputs_us'] for x in aa);tb=sum(x['total_completion_us']+x['setup_fresh_including_shared_inputs_us'] for x in bb);vals.append(math.log(ta/tb));totals.append(dict(block=bl,candidate_us=ta,reference_us=tb))
 if vals:paid.append(dict(policies=[a,b],totals=totals,scope='ACCOUNTED_SHARED_INPUT_POOL_PLUS_MEASURED_SELECTED_PLAN_PLUS_ACTUAL_128_REQUEST_TRACE; input pool measured once/shared in experiment, one copy billed to each separate fresh deployment scenario; not a separately executed cold process',**ci(vals,.975 if a=='RESOURCE' else .95)))
write(D/'trace_with_setup_accounting.json',paid)
life=gather('S5_lifecycle_*','lifecycle.jsonl');lifesummary=[]
for h in [1,32,1024,4096]:
 for p in ['SHAPE','RESOURCE','INIT_TUNE']:
  bs=sorted(set(x['block'] for x in life));values=[];sums=[]
  for b in bs:
   rr=[x for x in life if x['block']==b];ta=sum(next(y for y in x['records'] if y['H']==h)['total_lifecycle_us'] for x in rr if x['policy']==p);tb=sum(next(y for y in x['records'] if y['H']==h)['total_lifecycle_us'] for x in rr if x['policy']=='LIB_ALWAYS')
   if ta and tb:values.append(math.log(ta/tb));sums.append(dict(block=b,candidate_us=ta,lib_us=tb))
  if values:lifesummary.append(dict(H=h,policy=p,scope='MEASURED_H' if h<=32 else 'ESTIMATED_H_FROM_64_STEADY_REQUESTS',totals=sums,**ci(values)))
write(D/'lifecycle_summary.json',lifesummary)
counts=dict(aa_episodes=len(aa_records),calibration_quartets=len(gather('S2_pairs_*','pairs.jsonl')),card_episodes=len(gather('S2_card_*','phases.jsonl')),formal_quartets=len(pairs),direct_quartets=len(direct),formal_AA_quartets=len(anchors),deployment_phases_by_stage=dict(collections.Counter(x['stage'] for x in phases)),ffn_aliases=len(aliases),lifecycle_phases=len(life),lifecycle_H_records=sum(len(x['records']) for x in life),lifecycle_sample_records=len(gather('S5_lifecycle_*','lifecycle_samples.jsonl')),tuner_quartets=len(gather('S5_lifecycle_*','tuner_pairs.jsonl')))
write(D/'inventory.json',counts);print(json.dumps(counts,indent=2))
