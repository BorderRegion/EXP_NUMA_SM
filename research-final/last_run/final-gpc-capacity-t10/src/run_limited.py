from common import *
import subprocess,sys,time
assert read(RUN/'freeze/STATE_CONTROL.json')['branch']=='CONTROL_LIMITED'
def run(name,script,*args):
 p=subprocess.run([PYTHON,str(ROOT/'src/worker.py'),name,PYTHON,str(ROOT/'src'/script),*map(str,args)])
 if p.returncode:raise SystemExit(p.returncode)
subprocess.run([PYTHON,str(ROOT/'src/protocol_freeze.py')],check=True)
run('P0_RANGE_QUALIFICATION','qualify_range.py')
for b in range(2):
 run(f'P2_LIMITED_MICRO_{b}','measure_capacity.py',b,'--limited')
 run(f'P2_LIMITED_GQA_{b}','limited_micro_gqa.py',b)
for b in range(2):run(f'P3_DEV_{b}','measure_application.py','DEV',b,'--limited')
subprocess.run([PYTHON,str(ROOT/'src/opportunity.py')],check=True)
subprocess.run([PYTHON,str(ROOT/'src/freeze_capacity.py')],check=True)
for b in range(2):run(f'P4_LIMITED_{b}','measure_application.py','CONFIRM',b,'--limited')
for kind in ['memcheck','synccheck']:
 cmd=[PYTHON,str(ROOT/'src/worker.py'),'P5_'+kind,'/home/ubuntu/projects/leetgpu-lab/cuda/usr/bin/compute-sanitizer','--tool',kind,'--error-exitcode','42',PYTHON,str(ROOT/'src/sanitize_range.py')]
 subprocess.run(cmd,check=True)
write(RUN/'GPU_COMPLETE.json',dict(status='PASS',utc=utc(),branch='CONTROL_LIMITED',full_protocol_not_run=True))
print('LIMITED_GPU_COMPLETE',flush=True)
