from features import *
from train_rules import train
from dataclasses import asdict
import statistics,time
start=time.perf_counter();bins=read(ROOT/'freeze/bins.json');card=read(ROOT/'freeze/RESOURCE_CARD.json');cases={c['id']:c for c in read(INPUT/'plans/cases.json') if c['split']=='development'};scales=np.std(np.log2([[c['M'],c['N'],c['K']] for c in cases.values()]),axis=0).tolist()
rows=sum([lines(worker_dir(f'S2_action_{b}')/'phases.jsonl') for b in range(3)],[]);assert len(rows)==576
for b in range(2):
 for r in lines(worker_dir(f'S2_base_{b}')/'phases.jsonl'):
  if r['action']=='SINGLE' and r['recipe']==bins[bin_id(cases[r['case']])]['single_recipe']:rows.append(r)
trainrows=[]
for r in rows:
 c=cases[r['case']];sf,hf=features(c,r['action'],bins,card,scales);trainrows.append(dict(cohort='development',case_id=r['case'],action=r['action'],cpu_ready_us=r['cpu_ready_us'],shape_features=sf,resource_features=hf,source_phase=r['phase_id'],source_stage=r['stage'],source_block=r['block']))
write(ROOT/'freeze/TRAINING_ROWS.json',trainrows);models,result=train(trainrows)
setup=lines(worker_dir('S2_setup')/'setup_costs.jsonl');assert len(setup)==54;costs={b:{a:next(x['setup_us'] for x in setup if x['bin']==b and x['action']==a) for a in ACTIONS} for b in bins}
result.update(created_at=utc(),bins=bins,shape_distance_scales=scales,resource_card_sha256=sha(ROOT/'freeze/RESOURCE_CARD.json'),action_setup_us_by_bin=costs,static_resource_features=feature_static_card(card),representative_log_shapes=np.log2([r['shape'] for r in card['representatives']]).tolist(),expected_reuse_main=1024,selection_us=0.,selection_cost_status='PROVISIONAL_PENDING_COMPILED_CPU_MICROBENCH',resource_profile_scope='Card already built and cached. Fresh-device card/fit cost reported separately in lifecycle, not silently amortized.',training_timing_epochs='SINGLE selected-recipe rows from two base scans; LIB/SPLIT/PC rows from same three subsequent action blocks. Both selectors see exactly the same rows; this calibration difference is not a paired causal effect.',cpu_fit_seconds=time.perf_counter()-start)
write(ROOT/'freeze/POLICY_MODEL_PROVISIONAL.json',result)
print('TRAINED',len(cases),'cases',len(trainrows),'rows',result['cpu_fit_seconds'])
