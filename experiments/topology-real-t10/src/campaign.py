from common import *
from worker import run
import subprocess
if __name__=='__main__':
    write(ROOT/'freeze/IMPLEMENTATION.json',dict(created_utc=utc(),hashes={str(p.relative_to(ROOT)):sha(p) for d in ['src','build'] for p in (ROOT/d).rglob('*') if p.is_file() and '__pycache__' not in p.parts},protocol_sha256=sha(ROOT/'freeze/PROTOCOL.json')))
    run('qualification',[PYTHON,ROOT/'src/qualify.py','{OUT}'],timeout=120)
    san=REPO/'vendor/cuda_sanitizer_api-linux-x86_64-12.8.93-archive/bin/compute-sanitizer'
    for name in ['memcheck','synccheck']:
        run(name,[san,'--tool',name,'--error-exitcode','9',PYTHON,ROOT/'src/qualify.py','{OUT}','san'],timeout=180)
    run('racecheck_targeted',[san,'--tool','racecheck','--kernel-name','kns=paired','--launch-count','1','--error-exitcode','9',PYTHON,ROOT/'src/qualify.py','{OUT}','san'],timeout=120)
    for i in range(2):run(f'dev_{i}',[PYTHON,ROOT/'src/experiment.py','{OUT}','dev',i],timeout=120)
    subprocess.run([PYTHON,ROOT/'src/analyze.py','select'],check=True)
    for i in range(6):run(f'confirm_{i}',[PYTHON,ROOT/'src/experiment.py','{OUT}','confirm',i],timeout=300)
    write(ROOT/'reports/GPU_COMPLETE.json',dict(status='COMPLETE',created_utc=utc()))
    subprocess.run([PYTHON,ROOT/'src/analyze.py','final'],check=True)
