from common import *
from worker import run
import subprocess
assert (RUN/'vector_confirmation_5/complete.json').exists()
with (ROOT/'reports/VECTOR_ANALYSIS.log').open('w') as f:subprocess.run([PYTHON,str(ROOT/'src/analyze_vector.py')],stdout=f,stderr=subprocess.STDOUT,check=True)
r=read(ROOT/'derived/VECTOR_RESULTS.json')['vector_confirmation'];sel=read(ROOT/'freeze/VECTOR_SELECTION.json')['cases'];deploy={}
for cid in sel:
 deploy[cid]={}
 for mode in ['attention','append']:
  a=r['contrasts'][mode]['gpu_us'][cid]['ROUTE/STRONG_OLD'];b=r['contrasts'][mode]['host_us'][cid]['ROUTE/STRONG_OLD']
  passed=a['ci98_75_four_case'][0]>0 and a['positive_processes']==6 and b['ci95'][0]>0
  deploy[cid][mode]=sel[cid][mode]['candidate'] if passed else 'PREVIOUS_DEPLOYED'
write(ROOT/'freeze/DEPLOYMENT_POLICY.json',dict(created_utc=utc(),scope='Candidate policies frozen on development; gate to deploy after confirmation. No independent routing performance claim. Vectorization and work balancing, not physical NUMA success.',cases=deploy))
san=str(REPO/'vendor/cuda_sanitizer_api-linux-x86_64-12.8.93-archive/bin/compute-sanitizer');filters=[]
for G in [4,8]:
 for queue in [0,1]:
  for fused in [0,1]:filters+=['--kernel-name',f'kne=_Z6decodeILi128ELi{G}ELb{queue}ELb{fused}ELb0EEv6Params']
run('vector_racecheck',[san,'--tool','racecheck','--error-exitcode','70',*filters,PYTHON,str(ROOT/'src/vector_qualify.py'),'{OUT}','--small'],timeout=100)
run('vector_trace',[PYTHON,str(ROOT/'src/vector_trace.py'),'{OUT}'],timeout=100)
locked=[ROOT/'src/locality_plan.py',ROOT/'src/verify_api.py',ROOT/'freeze/DEPLOYMENT_POLICY.json',ROOT/'build/vector.so',ROOT/'build/vector_append.so']
write(ROOT/'freeze/API_SHA256.json',{str(p.relative_to(ROOT)):sha(p) for p in locked})
run('verify_public_api',[PYTHON,str(ROOT/'src/verify_api.py'),'{OUT}'],timeout=100)
print('FINAL_GPU_CHECKS_PASS')
