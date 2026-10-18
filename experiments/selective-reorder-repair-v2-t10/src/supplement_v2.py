from common import *
from policy_v2 import py_choice,POLICIES
import numpy as np,math,collections
r=runroot();d=r/'derived';model=read(ROOT/'freeze/POLICY_FREEZE.json');choices=read(ROOT/'freeze/choices_before_timing.json');cases=read(INPUT/'plans/cases.json');summ=[];differences=[];zero=[];margin=[]
for cohort in sorted(set(c['cohort'] for c in cases)):
 for dynamic in [False,True]:
  for policy in POLICIES:
   rr=[x for x in choices if x['cohort']==cohort and x['dynamic']==dynamic and x['policy']==policy];summ.append(dict(cohort=cohort,dynamic=dynamic,policy=policy,actions=dict(collections.Counter(x['chosen_action'] for x in rr)),raw_argmins=dict(collections.Counter(x['raw_argmin'] for x in rr)),bases=dict(collections.Counter(x['base_action'] for x in rr)),PC_on=sum(x['chosen_action'].startswith('PC') for x in rr),n=len(rr)))
for c in cases:
 for dynamic in [False,True]:
  rr={x['policy']:x for x in choices if x['case_id']==c['id'] and x['dynamic']==dynamic};differences.append(dict(case_id=c['id'],cohort=c['cohort'],dynamic=dynamic,shape=rr['SHAPE']['chosen_action'],resource=rr['RESOURCE']['chosen_action'],permuted=rr['PERMUTED_RESOURCE']['chosen_action'],resource_changes_shape=rr['SHAPE']['chosen_action']!=rr['RESOURCE']['chosen_action'],permutation_changes_resource=rr['RESOURCE']['chosen_action']!=rr['PERMUTED_RESOURCE']['chosen_action']))
  for policy in ['BASE','SHAPE','RESOURCE','PERMUTED_RESOURCE']:
   ch=rr[policy]
   if not ch['predictions']:continue
   z=py_choice(c,policy,1024,dynamic,model,zero_margin=True);zero.append(dict(case_id=c['id'],cohort=c['cohort'],policy=policy,dynamic=dynamic,actual=ch['chosen_action'],zero_margin_action=z['chosen_action'],scope='POSTHOC_CPU_DIAGNOSTIC_ONLY_NOT_A_DEPLOYED_METHOD'))
   for a in ch['candidates']:
    if a['base']!=('LIB' if a['action'] in ['SINGLE','SPLIT'] else ch['base_action']):continue
    margin.append(dict(case_id=c['id'],cohort=c['cohort'],policy=policy,dynamic=dynamic,**a,q_effective_us=a['predicted_base_us']*math.expm1(a['q_log']),raw_predicts_faster=a['predicted_ratio']<1,risk_blocks=a['predicted_ratio']<1 and a['upper_ratio']>=1,cost_blocks=a['upper_ratio']<1 and a['score']>=1,AA_dominates=a['aa_log']>=a['model_q_log']))
write(d/'choice_summary.json',summ);write(d/'action_disagreements.json',differences);write(d/'zero_margin_cpu_diagnostic.json',zero);write(d/'margin_scale_and_closures.json',margin)
counts=[]
for p in sorted((r/'raw').glob('S5_trace_*')):
 phase={x['phase_id']:x for x in lines(p/'phases.jsonl')}
 for x in lines(p/'samples.jsonl'):
  row=phase[x['phase_id']];counts.append(dict(block=row['block'],trace=row['case'],policy=row['policy'],requests=len(x['samples']),actual_action_counts=dict(collections.Counter(z['action'] for z in x['samples'])),n_signatures=len(row['signature_ids']),contains_all_16_new=set(c['id'] for c in cases if c['cohort']=='new_confirmation')<=set(row['signature_ids'])))
write(d/'actual_trace_action_counts.json',counts)
ledger=lines(r/'ledger.jsonl');components=[]
for worker in ledger:
 p=Path(worker['out']);p=r/'raw'/p.name;kind=worker['key']
 if not kind.startswith('S2'):continue
 measured=0;warm=0
 for fn in ['pairs.jsonl','anchors.jsonl']:
  for row in lines(p/fn):
   for w in row['windows']:measured+=w['window_host_us'];warm+=w['warm_cpu_us']
 for fn in ['phases.jsonl','stages.jsonl']:
  for row in lines(p/fn):
   if 'window' in row:measured+=row['window']['window_host_us'];warm+=row['window']['warm_cpu_us']
 science=lines(p/'scientific_costs.jsonl');card=lines(p/'cost_components.jsonl');cond=lines(p/'conditioning.jsonl')
 components.append(dict(worker=kind,worker_wall_s=worker['worker_s'],paired_or_card_measured_region_s=measured/1e6,per_window_warm_region_s=warm/1e6,native_conditioning_s=sum(x['seconds'] for x in cond),separately_measured_numerical_validation_s=(sum(x['qualification_us'] for x in science)+sum(x['numerical_scientific_us'] for x in card))/1e6 if science or card else None,validation_scope='Separate timing added prospectively after calibration process0 had started; missing is NA, never0. Includes JSON in card qualification but not pair qualification.'))
fit=model['fit_cpu_s'];compile_rows=[read(p) for p in (ROOT/'build').glob('*/build.json')];offline=dict(components=components,model_fit_cpu_s=fit,resource_card_aggregation_cpu_s=model['card'].get('card_aggregation_cpu_s'),host_compile_s=[x['cpu_build_s'] for x in compile_rows],full_production_cold_start_s=None,unseparated=['Calibration process0 scientific validation versus ordinary setup','Whole Python/CUDA/cublas process cold-start decomposition','Minimal production calibration effort versus this conservative research protocol'],scope='Worker time includes scientific checks and is NOT charged as mandatory production calibration. Only measured components are provided; full fresh-device/model lifecycle total is NA where inseparable, not zero. Cached actual deployment/lifecycle totals remain measured.')
write(d/'offline_cost_components.json',offline)
# Actual steady ratios underlying H estimates; break-even is diagnostic only.
life=[x for p in (r/'raw').glob('S5_lifecycle_*') for x in lines(p/'lifecycle.jsonl')];breaks=[]
for cid in sorted(set(x['case'] for x in life)):
 for p in ['SHAPE','RESOURCE','INIT_TUNE']:
  for b in sorted(set(x['block'] for x in life)):
   a=next((x for x in life if x['case']==cid and x['block']==b and x['policy']==p),None);z=next((x for x in life if x['case']==cid and x['block']==b and x['policy']=='LIB_ALWAYS'),None)
   if not a or not z:continue
   aa=next(x for x in a['records'] if x['H']==4096);bb=next(x for x in z['records'] if x['H']==4096);delta=bb['request_result']['cpu_ready_us']-aa['request_result']['cpu_ready_us'];extra=aa['setup_including_input_and_tuning_us']-bb['setup_including_input_and_tuning_us'];breaks.append(dict(case_id=cid,block=b,policy=p,steady_saving_us=delta,extra_setup_us=extra,point_break_even_calls=max(0,extra)/delta if delta>0 else None,scope='Uncertain per-block algebra only. No payback promise without independently supported steady advantage.'))
write(d/'break_even_diagnostics.json',breaks)
print('SUPPLEMENT_COMPLETE',len(margin),'margin records')
