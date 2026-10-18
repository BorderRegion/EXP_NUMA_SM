from common import *
from worker import run
import shutil
assert (RUN/'append_5/complete.json').exists()
run('vector_qualification',[PYTHON,str(ROOT/'src/vector_qualify.py'),'{OUT}'],timeout=90)
san=str(REPO/'vendor/cuda_sanitizer_api-linux-x86_64-12.8.93-archive/bin/compute-sanitizer')
for name in ['memcheck','synccheck']:
 run('vector_'+name,[san,'--tool',name,'--error-exitcode','70',PYTHON,str(ROOT/'src/vector_qualify.py'),'{OUT}','--small'],timeout=90)
snap=ROOT/'freeze/vector_implementation';snap.mkdir()
for name in ['vector_attention.cu','vector_append.cu','vector_runtime.py','vector_experiment.py','vector_qualify.py','select_vector.py','run_vector.py']:shutil.copy2(ROOT/'src'/name,snap/name)
locked=[*snap.glob('*'),ROOT/'freeze/VECTOR_PROTOCOL.json',ROOT/'build/vector.so',ROOT/'build/vector_append.so']
write(ROOT/'freeze/VECTOR_SHA256.json',{str(p.relative_to(ROOT)):sha(p) for p in locked})
for p in range(2):run(f'vector_dev_{p}',[PYTHON,str(ROOT/'src/vector_experiment.py'),'{OUT}','vector_dev',str(p)],timeout=160)
from select_vector import compute
x=compute();x['frozen_utc']=utc();write(ROOT/'freeze/VECTOR_SELECTION.json',x);print('VECTOR_FROZEN',json.dumps(x),flush=True)
for p in range(6):run(f'vector_confirmation_{p}',[PYTHON,str(ROOT/'src/vector_experiment.py'),'{OUT}','vector_confirmation',str(p)],timeout=200)
print('VECTOR_CAMPAIGN_COMPLETE')
