from common import *
from worker import run
from analyze import run as analyze
import subprocess
if __name__=='__main__':
 assert read(RUN/'qualification/complete.json')['status']=='PASS'
 for rel,h in read(ROOT/'freeze/IMPLEMENTATION.json')['hashes'].items():assert sha(ROOT/rel)==h
 san=str(REPO/'vendor/cuda_sanitizer_api-linux-x86_64-12.8.93-archive/bin/compute-sanitizer')
 for mode in ['memcheck','synccheck','racecheck']:run(mode+'_v2' if mode=='memcheck' else mode,[san,'--tool',mode,'--error-exitcode','9',PYTHON,ROOT/'src/qualify.py','{OUT}','--small'])
 for i in range(2):run(f'dev_{i}',[PYTHON,ROOT/'src/experiment.py','{OUT}','dev',i],timeout=400)
 analyze('dev',freeze=True)
 for i in range(6):run(f'confirm_{i}',[PYTHON,ROOT/'src/experiment.py','{OUT}','confirm',i],timeout=400)
 run('diagnose',[PYTHON,ROOT/'src/diagnose.py','{OUT}'],timeout=180)
 analyze('confirm');write(ROOT/'reports/GPU_COMPLETE.json',dict(created_utc=utc(),status='COMPLETE',next='CPU audit and delivery; no further GPU tuning'))
 print('CAMPAIGN_GPU_COMPLETE',flush=True)
