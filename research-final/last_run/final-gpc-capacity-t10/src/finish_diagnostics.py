from common import *
import subprocess
for kind in ['memcheck','synccheck']:
 subprocess.run([PYTHON,str(ROOT/'src/worker.py'),'P5_'+kind+'_installed','/home/ubuntu/文档/ChatGPT/numa_gpu/vendor/cuda_sanitizer_api-linux-x86_64-12.8.93-archive/bin/compute-sanitizer','--tool',kind,'--error-exitcode','42',PYTHON,str(ROOT/'src/sanitize_range.py')],check=True)
for name,script in [('P5_FOUR_PROFILES','profile_range.py'),('P5_BODY_DIAGNOSTIC','body_diagnostic.py')]:
 subprocess.run([PYTHON,str(ROOT/'src/worker.py'),name,PYTHON,str(ROOT/'src'/script)],check=True)
write(RUN/'GPU_COMPLETE.json',dict(status='PASS',utc=utc(),branch='CONTROL_LIMITED',full_protocol_not_run=True));print('LIMITED_GPU_COMPLETE',flush=True)
