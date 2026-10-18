from common import *
from worker import run
import shutil
san=str(REPO/'vendor/cuda_sanitizer_api-linux-x86_64-12.8.93-archive/bin/compute-sanitizer')
probe=[PYTHON,str(ROOT/'src/sanitize_probe.py'),'{OUT}']
for tool in ['memcheck','synccheck']:
 run(tool,[san,'--tool',tool,'--error-exitcode','70',*probe],timeout=90)
filters=[]
for D,G in [(128,4),(256,4),(128,8)]:
 for queue in [0,1]:
  for fused in [0,1]:filters+=['--kernel-name',f'kne=_Z6decodeILi{D}ELi{G}ELb{queue}ELb{fused}ELb0EEv6Params']
try:run('racecheck_targeted',[san,'--tool','racecheck','--error-exitcode','70',*filters,*probe],timeout=90)
except Exception as ex:
 write(ROOT/'reports/RACECHECK_EXCEPTION.json',dict(error=repr(ex),status='NOT_PASS_REQUIRES_REVIEW'));raise
snapshot=ROOT/'freeze/implementation';snapshot.mkdir(exist_ok=False)
for p in (ROOT/'src').glob('*'):
 if p.is_file():shutil.copy2(p,snapshot/p.name)
locked=[*snapshot.glob('*'),ROOT/'freeze/PROTOCOL.json',ROOT/'build/attention.so'];write(ROOT/'freeze/EXECUTION_SHA256.json',{str(p.relative_to(ROOT)):sha(p) for p in locked})
for process in range(2):run(f'development_{process}',[PYTHON,str(ROOT/'src/experiment.py'),'{OUT}','development',str(process)],timeout=300)
from select_config import compute
x=compute();x['frozen_utc']=utc();write(ROOT/'freeze/SELECTION.json',x)
for process in range(6):run(f'confirmation_{process}',[PYTHON,str(ROOT/'src/experiment.py'),'{OUT}','confirmation',str(process)],timeout=180)
print('CAMPAIGN_COMPLETE')
