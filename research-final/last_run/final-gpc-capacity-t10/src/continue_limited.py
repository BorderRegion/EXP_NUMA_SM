from common import *
import subprocess

def worker(name,script,*args):
 subprocess.run([PYTHON,str(ROOT/'src/worker.py'),name,PYTHON,str(ROOT/'src'/script),*map(str,args)],check=True)
write(RUN/'freeze/DIAGNOSTIC_EVENT_REPAIR.json',dict(utc=utc(),repair='materialized EXTERNAL diagnostic events only; no mathematical/formal DAG changes',hashes={str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'src/range_extensions.inc',ROOT/'src/measure_application.py',ROOT/'build/bridge_capacity.so',ROOT/'build/range_gqa.so']}))
worker('P3_DEV_0_retry2','measure_application.py','DEV',0,'--limited')
worker('P3_DEV_1','measure_application.py','DEV',1,'--limited')
subprocess.run([PYTHON,str(ROOT/'src/opportunity.py')],check=True)
subprocess.run([PYTHON,str(ROOT/'src/freeze_capacity.py')],check=True)
for b in range(2):worker(f'P4_LIMITED_{b}','measure_application.py','CONFIRM',b,'--limited')
for kind in ['memcheck','synccheck']:
 subprocess.run([PYTHON,str(ROOT/'src/worker.py'),'P5_'+kind,'/home/ubuntu/projects/leetgpu-lab/cuda/usr/bin/compute-sanitizer','--tool',kind,'--error-exitcode','42',PYTHON,str(ROOT/'src/sanitize_range.py')],check=True)
write(RUN/'GPU_COMPLETE.json',dict(status='PASS',utc=utc(),branch='CONTROL_LIMITED',full_protocol_not_run=True))
print('LIMITED_GPU_COMPLETE',flush=True)
