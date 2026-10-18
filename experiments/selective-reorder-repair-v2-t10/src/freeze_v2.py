from common import *
import sys,time,math,numpy as np,subprocess,ctypes as C
sys.path.insert(0,str(ROOT/'reference'))
from relative_policy import train,Linear,FeatureBank
from paired_stats import quantile,latency_bucket
from policy_v2 import py_choice,POLICIES
import csv
state_checks=[]
for folder in sorted((runroot()/'raw').glob('S[12]_*')):
 mf=read(folder/'manifest.json');assert mf['status']=='COMPLETED',folder
 for t in csv.DictReader((folder/'telemetry.csv').open()):
  if t['requested_limit_mw']!='100000' or t['enforced_limit_mw']!='100000' or (t['throttle_reasons'].isdigit() and int(t['throttle_reasons'])&(32|64)):state_checks.append(dict(worker=folder.name,sample=t))
write(ROOT/'reports/PRE_FIT_HARD_STATE_CHECK.json',dict(status='PASS' if not state_checks else 'REQUIRES_STATE_SEPARATION',events=state_checks,scope='1Hz sampled power/thermal state; ordinary dynamic clocks remain in the data.'))
assert not state_checks,'Do not silently mix a hard power/thermal state in calibration'
start=time.perf_counter();pairs=[]
for b in range(3):
 r=lines(worker_dir(f'S2_pairs_{b}')/'pairs.jsonl');assert len(r)==384;pairs+=r
cases=read(INPUT/'plans/cases.json');card=read(ROOT/'freeze/RESOURCE_CARD.json');bins={k:{q:v[q] for q in ['single_recipe','split_recipe','split_S']} for k,v in read(ROOT/'freeze/bins.json').items()};fitpairs=[{k:r[k] for k in ['case_id','action','block','round','protocol_id','state_epoch','cohort','log_ratio','reference_geomean_us','quartet_id']} for r in pairs];payload=dict(cases=cases,bins=bins,card=card,pairs=fitpairs)
write(ROOT/'freeze/TRAINING_INPUT.json',payload);model=train(payload);model.update(version='20261017-repair-v2',bins=bins,card=card,dynamic_selection_delta_us=0.,created_at=utc(),fit_cpu_s=time.perf_counter()-start,fit_timing_scope='CPU-only input loading/serialization plus fit and LOSO wall interval, not processor-cycle time',action_setup_us_by_bin={})
setup=lines(worker_dir('S2_setup')/'setup_costs.jsonl');assert len(setup)==54
for bid in sorted(bins):model['action_setup_us_by_bin'][bid]={a:next(x['setup_us'] for x in setup if x['bin']==bid and x['action']==a) for a in ACTIONS}
# The noise floor is estimated only from the S1 CLEAN episodes, then mapped
# using the development-fitted LIB scale model. No confirmation timings enter.
fb=FeatureBank(cases,bins,card);noise=[]
for b in range(2):
 for row in lines(worker_dir(f'S1_aa_{b}')/'aa.jsonl'):
  if row['history']!='CLEAN':continue
  t=math.exp(Linear(**model['lib_scale_model']).predict(fb.shape_vector(row['case_id'],'LIB')))
  for r in row['contrasts']:noise.append(dict(case=row['case_id'],block=b,predicted_lib_us=t,bucket=latency_bucket(t),abs_log=abs(r['log_ratio'])))
assert len(noise)==24;pooled=quantile([x['abs_log'] for x in noise],.9);model['aa_floor_log']={};model['aa_floor_detail']={}
for b in range(3):
 rr=[x for x in noise if x['bucket']==b];model['aa_floor_log'][str(b)]=quantile([x['abs_log'] for x in rr],.9) if rr else pooled;model['aa_floor_detail'][str(b)]=dict(n_quartets=len(rr),n_shapes=len(set(x['case'] for x in rr)),source='bucket_clean_AA_absolute_log_q90' if rr else 'pooled_clean_AA_absolute_log_q90',q_log=model['aa_floor_log'][str(b)])
model['aa_observations']=noise;model['setup_scope']='Already initialized CUDA, selected engine/resources/partial/four prepared slot graphs; input generation separate; single sample per action/bin; explicit DAG/node observation subtracted and recorded; no scientific roster qualification billed.'
write(ROOT/'freeze/POLICY_FREEZE.json',model)
def generate_compile(name):
 subprocess.run([PYTHON,str(ROOT/'src/generate_v2.py')],check=True)
 subprocess.run(['g++','-std=c++17','-O3','-shared','-fPIC',str(ROOT/'src/policy_cpu.cpp'),'-o',str(ROOT/'build'/name)],check=True)
generate_compile('policy_cpu_pilot.so');cpu=C.CDLL(str(ROOT/'build/policy_cpu_pilot.so'));cpu.sr_choice_bench.argtypes=[C.c_int]*6;cpu.sr_choice_bench.restype=C.c_double
bench=[]
for c in cases[:24]:
 for p in range(1,5):
  for repeat in range(3):bench.append(dict(case=c['id'],policy=p,repeat=repeat,batch=1000,mean_us=cpu.sr_choice_bench(c['M'],c['N'],c['K'],p,1024,1000)))
model['dynamic_selection_delta_us']=float(np.quantile([x['mean_us'] for x in bench],.95));model['selection_measurement_scope']='95th percentile of 1000-call batch means over 24 development shapes x four policies x three repeats; not individual request p95; volatile shape loads prevent loop-invariant prediction hoisting; conservative full selection cost, fixed bound steady delta=0.'
write(ROOT/'reports/SELECTOR_CPU_TIMING.json',bench);write(ROOT/'freeze/POLICY_FREEZE.json',model);generate_compile('policy_cpu_frozen.so')
# CDLL keeps the first loaded shared object alive; load the final generated file under a fresh name.
import shutil
shutil.copy2(ROOT/'build/policy_cpu_frozen.so',ROOT/'build/policy_cpu.so');cpu=C.CDLL(str(ROOT/'build/policy_cpu_frozen.so'));cpu.v2_choose_cpu.argtypes=[C.c_int]*6+[C.POINTER(C.c_double)]
checks=[];choices=[]
for c in cases:
 for p in range(5):
  for h in [0,1,32,256,1024,4096]:
   for dyn in [False,True]:
    d=py_choice(c,p,h,dyn,model);v=(C.c_double*13)();cpu.v2_choose_cpu(c['M'],c['N'],c['K'],p,h,int(dyn),v)
    assert d['base_action']==ACTIONS[int(v[0])] and d['chosen_action']==ACTIONS[int(v[1])],(c,p,h,dyn,d,list(v))
    if d['predictions'] is not None:
     assert abs(v[12]-(d['upper_ratio']+d['cost_ratio']))<1e-10,(c,p,h,dyn,'SCORE_MISMATCH')
     assert int(v[2])==(4 if d['chosen_action']!=d['base_action'] else 3)
    err=0 if d['predictions'] is None else max(abs(v[3+i]-d['predictions'][a])/max(1,d['predictions'][a]) for i,a in enumerate(ACTIONS));assert err<1e-11,err
    checks.append(dict(case=c['id'],policy=POLICIES[p],H=h,dynamic=dyn,relative_prediction_error=err,action=d['chosen_action']))
    if h==1024:choices.append(dict(case_id=c['id'],cohort=c['cohort'],policy=POLICIES[p],**d))
write(ROOT/'reports/NEW_CPU_EQUIVALENCE.json',dict(status='PASS',comparisons=len(checks),max_relative_prediction_error=max(x['relative_prediction_error'] for x in checks),rows=checks))
write(ROOT/'freeze/choices_before_timing.json',choices)
vgs=sorted(c['id'] for c in cases if c['cohort'] in ['new_confirmation','regression'])
if not vgs:vgs=sorted(c['id'] for c in cases if c['split'] in ['confirmation','regression'])
witness=[]
for cid in vgs:
 rr=[x for x in choices if x['case_id']==cid and x['dynamic'] and x['policy'] in ['SHAPE','RESOURCE','PERMUTED_RESOURCE']]
 if len(set(x['chosen_action'] for x in rr))>1:witness.append(cid)
witness=witness[:6];write(ROOT/'freeze/witness.json',dict(case_ids=witness,requests=[witness[i%len(witness)] for i in range(96)] if witness else [],selection='Frozen action disagreement in V/G sorted by ID; first six; no GPU evaluation timings',status='ACTION_CHANGING' if witness else 'NO_ACTION_DISAGREEMENT'))
write(ROOT/'freeze/FREEZE_SEAL.json',dict(created_at=utc(),model_sha=sha(ROOT/'freeze/POLICY_FREEZE.json'),choices_sha=sha(ROOT/'freeze/choices_before_timing.json'),cpp_sha=sha(ROOT/'src/policy.hpp'),cpp_sources={p.name:sha(p) for p in (ROOT/'src').glob('*') if p.suffix in ['.hpp','.cu','.cuh']},cpu_binary_sha=sha(ROOT/'build/policy_cpu_frozen.so'),witness_sha=sha(ROOT/'freeze/witness.json'),training_protocol=STATE if False else model['source_protocol']))
from collections import Counter
print('FROZEN',Counter((x['policy'],x['dynamic'],x['chosen_action']) for x in choices if x['cohort']=='new_confirmation'));print('AA',model['aa_floor_log'],'selector_us',model['dynamic_selection_delta_us'],'WITNESS',witness)
