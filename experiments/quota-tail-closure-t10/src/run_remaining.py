from common import *
import subprocess
def cpu(name):subprocess.run([PYTHON,str(ROOT/'src'/name)],check=True)
def worker(stage,block):subprocess.run([PYTHON,str(ROOT/'src/worker.py'),f'{stage}_block_{block}',PYTHON,str(ROOT/'src/experiments.py'),stage,str(block)],check=True)
assert read(RUN/'raw/S1_block_0_retry/manifest.json')['status']=='COMPLETED'
worker('S1',1);cpu('freeze_prefix.py')
for b in [0,1]:worker('S2',b)
cpu('freeze_selection.py')
for b in range(2,8):worker('S3',b)
for b in range(8,12):worker('HOLDOUT',b)
print('ALL_PLANNED_TIMING_COMPLETE',flush=True)
