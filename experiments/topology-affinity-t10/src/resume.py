from common import *
from worker import run
import subprocess
if __name__=='__main__':
    # First campaign stopped on a missing CPU-only pandas import, before random
    # control selection and before any confirmation worker. Preserve its log.
    for i in range(2):assert read(RUN/f'dev_{i}/complete.json')['status']=='PASS'
    subprocess.run([PYTHON,ROOT/'src/analyze.py','dev','--select'],check=True)
    write(ROOT/'freeze/CONFIRMATION_EPOCH.json',dict(created_utc=utc(),reason='Install missing CPU analysis dependency; no GPU algorithm changes',
        original_implementation_sha256=sha(ROOT/'freeze/IMPLEMENTATION.json'),random_best_sha256=sha(ROOT/'freeze/RANDOM_BEST.json'),
        source_hashes={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'src').glob('*') if p.is_file()}))
    for i in range(6):run(f'confirm_{i}',[PYTHON,ROOT/'src/experiment.py','{OUT}','confirm',i],timeout=400)
    subprocess.run([PYTHON,ROOT/'src/analyze.py','confirm'],check=True)
    write(ROOT/'reports/PRIMARY_GPU_COMPLETE.json',dict(created_utc=utc(),status='COMPLETE'))
    for i in range(6):run(f'full_{i}',[PYTHON,ROOT/'src/full_direction.py','{OUT}',i],timeout=180)
    write(ROOT/'reports/GPU_COMPLETE.json',dict(created_utc=utc(),status='COMPLETE'))
    print('GPU CAMPAIGN COMPLETE',flush=True)
