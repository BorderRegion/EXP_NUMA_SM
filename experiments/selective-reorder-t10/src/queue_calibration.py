from worker import *
import subprocess
run('S1_sanitizer',[str(REPO/'vendor/cuda_sanitizer_api-linux-x86_64-12.8.93-archive/bin/compute-sanitizer'),'--tool','memcheck','--error-exitcode','97',PYTHON,ROOT/'src/qualify.py','{OUT}','small'])
for b in range(2):run(f'S2_base_{b}',[PYTHON,ROOT/'src/calibrate.py','{OUT}','base',b])
subprocess.run([PYTHON,str(ROOT/'src/freeze_bins.py')],check=True)
for b in range(3):run(f'S2_action_{b}',[PYTHON,ROOT/'src/calibrate.py','{OUT}','placement',b])
for b in range(2):run(f'S2_card_{b}',[PYTHON,ROOT/'src/calibrate.py','{OUT}','card',b])
write(runroot()/'CALIBRATION_COMPLETE.json',dict(at=utc(),status='COMPLETE'))
