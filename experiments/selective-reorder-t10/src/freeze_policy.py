from policy_api import *
import subprocess,numpy as np,time
provisional=ROOT/'freeze/POLICY_MODEL_PROVISIONAL.json';model=read(provisional)
def compile_model(path):
 subprocess.run([PYTHON,str(ROOT/'src/generate_policy.py'),str(path)],check=True)
 subprocess.run(['g++','-O3','-std=c++17','-shared','-fPIC',str(ROOT/'src/policy_cpu.cpp'),'-o',str(ROOT/'build/policy_cpu.so')],check=True)
compile_model(provisional);cpu=CPUChooser();cases=read(INPUT/'plans/cases.json');times=[]
for c in [x for x in cases if x['split']=='development']:
 for policy in [1,2,3,4]:
  for _ in range(3):times.append(dict(case=c['id'],policy=POLICIES[policy],us=cpu.lib.sr_choice_bench(c['M'],c['N'],c['K'],policy,1024,1000)))
model['selection_us']=float(np.quantile([x['us'] for x in times],.95));model['selection_cost_status']='P95_COMPILED_CPP_1000_DECISIONS_PER_BATCH_MEASURED_BEFORE_TEST';model['selection_cost_samples']=times;model['frozen_at']=utc();assert not MODEL_PATH.exists();write(MODEL_PATH,model)
compile_model(MODEL_PATH)
# New path prevents dlopen returning a cached provisional shared library.
import shutil
shutil.copy2(ROOT/'build/policy_cpu.so',ROOT/'build/policy_cpu_final.so');cpu=CPUChooser(ROOT/'build/policy_cpu_final.so');checks=[]
for c in cases:
 for policy in POLICIES:
  for h in [None,1,32,256,1024,4096]:
   cpp=cpu.choose(c,policy,h);py=py_choice(c,policy,h,model);assert cpp['chosen_action']==py['chosen_action'] and cpp['base_action']==py['base_action'],(c,policy,h,cpp,py)
   if py['predictions'] is not None:
    err=max(abs(cpp['predictions'][a]/py['predictions'][a]-1) for a in ACTIONS);assert err<1e-10,err
   else:err=0
   checks.append(dict(case=c['id'],policy=policy,H=h,action=cpp['chosen_action'],relative_prediction_error=err))
write(ROOT/'reports/CPP_EQUIVALENCE.json',dict(status='PASS',checks=checks));write(ROOT/'freeze/POLICY_FREEZE_HASHES.json',dict(frozen_at=utc(),files={str(p.relative_to(ROOT)):sha(p) for p in [MODEL_PATH,ROOT/'freeze/RESOURCE_CARD.json',ROOT/'freeze/bins.json',ROOT/'src/policy.hpp',ROOT/'build/policy_cpu_final.so']}))
# Decisions exist for every supplied shape before any test outcome is read.
write(ROOT/'freeze/ALL_CHOICES_BEFORE_TEST.json',[dict(case=c['id'],cohort=c['split'],policy=p,**cpu.choose(c,p,1024)) for c in cases for p in POLICIES]);print('FROZEN selection_us',model['selection_us'])
