from common import *
import subprocess
commands=[
 [PYTHON,str(ROOT/'src/run_single.py'),'E3'],
 [PYTHON,str(ROOT/'src/run_coexecution.py')],
 [PYTHON,str(ROOT/'src/worker.py'),'E5_profiles',PYTHON,str(ROOT/'src/profile_coexecution.py')],
]
for cmd in commands:
 p=subprocess.run(cmd,cwd=REPO)
 if p.returncode:raise SystemExit(p.returncode)
print('ALL_GPU_WORK_COMPLETE',flush=True)
