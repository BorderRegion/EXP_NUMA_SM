from worker import run
from common import *
import sys
mode=sys.argv[1];san=REPO/'vendor/cuda_sanitizer_api-linux-x86_64-12.8.93-archive/bin/compute-sanitizer'
if mode=='sanitizers':
 for kind in ['memcheck','synccheck','racecheck']:run(kind,[san,'--tool',kind,'--error-exitcode','99',PYTHON,ROOT/'src/qualify.py','{OUT}'],timeout=180)
else:
 n=2 if mode=='development' else 6
 for process in range(n):run(f'{mode}_{process}',[PYTHON,ROOT/'src/experiment.py','{OUT}',mode,process],timeout=180)
