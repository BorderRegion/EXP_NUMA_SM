from worker import run
from common import *
import sys
san=REPO/'vendor/cuda_sanitizer_api-linux-x86_64-12.8.93-archive/bin/compute-sanitizer'
mode=sys.argv[1]
if mode=='sanitizers':
 for kind in ['memcheck','synccheck']:
  run(kind,[san,'--tool',kind,'--error-exitcode','99',PYTHON,ROOT/'src/qualify.py','{OUT}'],timeout=180)
elif mode=='formal':
 for process in range(6):run(f'formal_{process}',[PYTHON,ROOT/'src/experiment.py','{OUT}','formal',process],timeout=180)
else:raise ValueError(mode)
