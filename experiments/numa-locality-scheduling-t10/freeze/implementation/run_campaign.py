from common import *
from worker import run
import shutil
san=str(REPO/'vendor/cuda_sanitizer_api-linux-x86_64-12.8.93-archive/bin/compute-sanitizer')
for name in ['memcheck','synccheck']:
 run(name,[san,'--tool',name,'--error-exitcode','70',PYTHON,str(ROOT/'src/qualify.py'),'{OUT}','--small'],timeout=90)
snap=ROOT/'freeze/implementation';snap.mkdir()
for p in (ROOT/'src').glob('*'):
 if p.is_file():shutil.copy2(p,snap/p.name)
locked=[*snap.glob('*'),ROOT/'freeze/PROTOCOL.json',ROOT/'freeze/LEGACY_SELECTION.json',ROOT/'build/attention.so',ROOT/'build/legacy/attention.so']
write(ROOT/'freeze/EXECUTION_SHA256.json',{str(p.relative_to(ROOT)):sha(p) for p in locked})
for process in range(2):run(f'development_{process}',[PYTHON,str(ROOT/'src/experiment.py'),'{OUT}','development',str(process)],timeout=240)
from select_config import compute
x=compute();x['frozen_utc']=utc();write(ROOT/'freeze/SELECTION.json',x)
print('FROZEN',json.dumps({k:{a:v[a] for a in ['static','coarse','replica','route']} for k,v in x['cases'].items()}),flush=True)
for process in range(6):run(f'confirmation_{process}',[PYTHON,str(ROOT/'src/experiment.py'),'{OUT}','confirmation',str(process)],timeout=160)
print('CAMPAIGN_COMPLETE')
