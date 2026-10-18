from common import *
from worker import run
import subprocess
if __name__=='__main__':
    assert read(ROOT/'reports/SHARED_GPU_COMPLETE.json')['status']=='COMPLETE'
    write(ROOT/'freeze/FAST_IMPLEMENTATION.json',dict(created_utc=utc(),hashes={str(p.relative_to(ROOT)):sha(p) for p in list((ROOT/'src').glob('*'))+[ROOT/'build/fast_fit.so'] if p.is_file()},protocol_sha256=sha(ROOT/'freeze/FAST_SETUP_PROTOCOL.json')))
    run('fs_qualification',[PYTHON,ROOT/'src/fast_experiment.py','{OUT}','qualify'],timeout=120)
    san=REPO/'vendor/cuda_sanitizer_api-linux-x86_64-12.8.93-archive/bin/compute-sanitizer'
    run('fs_memcheck',[san,'--tool','memcheck','--error-exitcode','9',PYTHON,ROOT/'src/fast_experiment.py','{OUT}','qualify'],timeout=180)
    for i in range(6):run(f'fast_{i}',[PYTHON,ROOT/'src/fast_experiment.py','{OUT}',i],timeout=180)
    subprocess.run([PYTHON,ROOT/'src/analyze.py','fast'],check=True)
    write(ROOT/'reports/FAST_GPU_COMPLETE.json',dict(created_utc=utc(),status='COMPLETE'))
    print('FAST GPU COMPLETE',flush=True)
