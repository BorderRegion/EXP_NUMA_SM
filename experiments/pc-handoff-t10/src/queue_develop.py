from worker import run
from common import *
import subprocess
# qualify_edges completed successfully in retained first queue invocation.
sanitizer=REPO/'vendor/cuda_sanitizer_api-linux-x86_64-12.8.93-archive/bin/compute-sanitizer'
assert sanitizer.exists()
run('sanitizer_edges_02',[sanitizer,'--tool','memcheck','--error-exitcode','86',PYTHON,ROOT/'src/qualify_edges.py','{OUT}'])
for b in range(2):run(f'E1_block_{b}',[PYTHON,ROOT/'src/develop.py','{OUT}',str(b)])
subprocess.run([PYTHON,ROOT/'src/select_development.py'],check=True)
print('E1_ALL_COMPLETE',flush=True)
