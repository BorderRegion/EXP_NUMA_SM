from common import *
from worker import run
import subprocess
if __name__=='__main__':
    assert read(RUN/'qualification/complete.json')['status']=='PASS'
    f=ROOT/'freeze/IMPLEMENTATION.json';assert not f.exists()
    paths=[p for part in ['src','build','support'] for p in (ROOT/part).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    write(f,dict(created_utc=utc(),hashes={str(p.relative_to(ROOT)):sha(p) for p in paths},protocol_sha256=sha(ROOT/'freeze/PROTOCOL.json')))
    san=REPO/'vendor/cuda_sanitizer_api-linux-x86_64-12.8.93-archive/bin/compute-sanitizer'
    for mode in ['memcheck','synccheck','racecheck']:
        run(mode,[san,'--tool',mode,'--error-exitcode','9',PYTHON,ROOT/'src/qualify.py','{OUT}','--small'],timeout=300)
    for i in range(2):run(f'dev_{i}',[PYTHON,ROOT/'src/experiment.py','{OUT}','dev',i],timeout=400)
    subprocess.run([PYTHON,ROOT/'src/analyze.py','dev','--select'],check=True)
    for i in range(6):run(f'confirm_{i}',[PYTHON,ROOT/'src/experiment.py','{OUT}','confirm',i],timeout=400)
    subprocess.run([PYTHON,ROOT/'src/analyze.py','confirm'],check=True)
    write(ROOT/'reports/GPU_COMPLETE.json',dict(created_utc=utc(),status='COMPLETE'))
    print('GPU CAMPAIGN COMPLETE',flush=True)
