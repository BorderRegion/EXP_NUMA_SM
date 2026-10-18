from common import *
from worker import run
from analyze import run as analyze
import subprocess
if __name__=='__main__':
 assert read(RUN/'qualification/complete.json')['status']=='PASS'
 freeze=ROOT/'freeze/IMPLEMENTATION.json';assert not freeze.exists();write(freeze,dict(created_utc=utc(),hashes={str(p.relative_to(ROOT)):sha(p) for p in list((ROOT/'src').glob('*'))+list((ROOT/'build').glob('*')) if p.is_file()},maps_sha256=sha(ROOT/'freeze/MAPS.json')))
 san='/home/ubuntu/projects/leetgpu-lab/cuda/usr/bin/compute-sanitizer'
 for mode in ['memcheck','synccheck','racecheck']:run(mode,[san,'--tool',mode,'--error-exitcode','9',PYTHON,ROOT/'src/qualify.py','{OUT}','--small'])
 for i in range(2):run(f'dev_{i}',[PYTHON,ROOT/'src/experiment.py','{OUT}','dev',i],timeout=400)
 analyze('dev',freeze=True)
 for i in range(6):run(f'confirm_{i}',[PYTHON,ROOT/'src/experiment.py','{OUT}','confirm',i],timeout=400)
 run('diagnose',[PYTHON,ROOT/'src/diagnose.py','{OUT}'],timeout=180)
 analyze('confirm');write(ROOT/'reports/GPU_COMPLETE.json',dict(created_utc=utc(),status='COMPLETE',next='CPU audit and delivery; no further GPU tuning'))
 print('CAMPAIGN_GPU_COMPLETE',flush=True)
