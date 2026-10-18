from worker import *
for b in range(6):
 run(f'S5_trace_{b}',[PYTHON,ROOT/'src/deployment_v2.py','{OUT}','trace',str(b)])
 run(f'S5_ffn_{b}',[PYTHON,ROOT/'src/deployment_v2.py','{OUT}','ffn',str(b)])
for b in range(3):
 for mode in ['binding','ood','witness']:
  if mode=='witness' and not read(ROOT/'freeze/witness.json')['case_ids']:continue
  run(f'S5_{mode}_{b}',[PYTHON,ROOT/'src/deployment_v2.py','{OUT}',mode,str(b)])
 run(f'S5_lifecycle_{b}',[PYTHON,ROOT/'src/lifecycle_v2.py','{OUT}',str(b)])
run('S6_profiles',[PYTHON,ROOT/'src/profiles.py','{OUT}'])
