from common import *
from worker import run
import subprocess
if __name__=='__main__':
    impl=read(ROOT/'freeze/IMPLEMENTATION.json')
    for name,h in impl['hashes'].items():assert sha(ROOT/name)==h,name
    sanitizer=REPO/'vendor/cuda_sanitizer_api-linux-x86_64-12.8.93-archive/bin/compute-sanitizer'
    run('racecheck_targeted',[sanitizer,'--tool','racecheck','--kernel-name','kns=tail','--launch-count','1','--error-exitcode','9',PYTHON,ROOT/'src/qualify.py','{OUT}','san'],timeout=120)
    for i in range(2):run(f'dev_{i}',[PYTHON,ROOT/'src/experiment.py','{OUT}','dev',i],timeout=240)
    subprocess.run([PYTHON,ROOT/'src/analyze.py','select'],check=True)
    for i in range(6):run(f'confirm_{i}',[PYTHON,ROOT/'src/experiment.py','{OUT}','confirm',i],timeout=240)
    write(ROOT/'reports/GPU_COMPLETE.json',dict(status='COMPLETE',created_utc=utc()))
    subprocess.run([PYTHON,ROOT/'src/analyze.py','final'],check=True)
