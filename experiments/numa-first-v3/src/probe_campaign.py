import subprocess,sys
from common import *
from worker import run
r=runroot();b=r/'compiled';mode=sys.argv[1]
if mode=='dev':
 sanitizer=REPO/'vendor/cuda_sanitizer_api-linux-x86_64-12.8.93-archive/bin/compute-sanitizer'
 run('P1','probe_memcheck',[sanitizer,'--tool','memcheck','--error-exitcode','42',b/'probe_runner','--cubin',b/'probe.cubin','--out','{OUT}','--allocation','91','--rounds','1','--small','1'])
 for allocation in [0,1]:
  out=run('P1',f'dev_{allocation}',[PYTHON,ROOT/'src/probe_job.py','--allocation',allocation,'--kind','main','--rounds',8,'--out','{OUT}'])
  subprocess.run([PYTHON,str(ROOT/'src/analyze_probe.py'),str(out)],check=True)
  out=run('P1',f'scout_{allocation}',[b/'probe_runner','--cubin',b/'probe.cubin','--allocation',allocation,'--kind','scout','--rounds',4,'--out','{OUT}'])
  subprocess.run([PYTHON,str(ROOT/'src/analyze_probe.py'),str(out)],check=True)
elif mode=='confirm':
 assert (r/'P1_CONFIRMATION_FREEZE.json').exists()
 for allocation in [2,3,4,5]:
  out=run('P1',f'confirm_{allocation}',[PYTHON,ROOT/'src/probe_job.py','--allocation',allocation,'--kind','main','--rounds',8,'--out','{OUT}'])
  subprocess.run([PYTHON,str(ROOT/'src/analyze_probe.py'),str(out)],check=True)
else:raise ValueError(mode)
