from worker import *
assert read(worker_dir('S3_deploy_qualify')/'complete.json')['status']=='PASS'
for b in range(6):run(f'S4_block_{b}',[PYTHON,ROOT/'src/formal.py','{OUT}',b])
for b in range(6):
 run(f'S5_trace_{b}',[PYTHON,ROOT/'src/deployment_runs.py','{OUT}','trace',b])
 run(f'S5_ffn_{b}',[PYTHON,ROOT/'src/deployment_runs.py','{OUT}','ffn',b])
for b in range(3):run(f'S5_ood_{b}',[PYTHON,ROOT/'src/deployment_runs.py','{OUT}','ood',b])
for b in range(3):run(f'S5_lifecycle_{b}',[PYTHON,ROOT/'src/lifecycle.py','{OUT}',b])
write(runroot()/'DEPLOYMENT_GPU_COMPLETE.json',dict(at=utc(),status='COMPLETE',reports_pending=True))
