"""Finite serial E1-E6 continuation; completed raw directories are never replaced."""
from worker import run
from common import *
import subprocess,time

def done(key):
 rows=[json.loads(x) for x in (runroot()/'ledger.jsonl').read_text().splitlines()] if (runroot()/'ledger.jsonl').exists() else []
 return any(x['key']==key and x['status']=='COMPLETED' for x in rows)
def work(key,script,*args):
 if done(key):return
 run(key,[PYTHON,ROOT/'src'/script,'{OUT}',*map(str,args)])
while not (ROOT/'freeze/selection.json').exists():
 time.sleep(5)
 if (runroot()/'GPU_HEALTH_STOP').exists():raise RuntimeError('GPU safety stop')
while not done('qualify_host_attention'):
 time.sleep(5)
 p=runroot()/'raw/qualify_host_attention/manifest.json'
 if p.exists() and json.loads(p.read_text())['status']=='FAILED':raise RuntimeError('Inspect qualified host/attention failure; no method data substituted')
work('E1_scope_checks','scopes.py')
for b in [0,1]:work(f'E2_matrix_{b}','pc_matrix.py',b)
if not (ROOT/'freeze/pc_rule.json').exists():subprocess.run([PYTHON,ROOT/'src/select_pc.py'],check=True)
for b in [2,3]:work(f'E2_matrix_{b}','pc_matrix.py',b)
for b in range(4):work(f'E2_bridge_{b}','pc_bridge.py',b)
if not (ROOT/'freeze/branch_choice.json').exists():subprocess.run([PYTHON,ROOT/'src/choose_branch.py'],check=True)
c=json.loads((ROOT/'freeze/branch_choice.json').read_text())
for b in range(c['blocks']):work(f'E3_block_{b}','formal.py',b,c['mode'])
work('E4_native_development','attention.py',0,'development')
for b in range(6):work(f'E4_native_{b}','attention.py',b,'test')
for b in range(6):work(f'E5_gemm_{b}','gemm_layers.py',b)
for b in range(6):work(f'E5_attention_{b}','attention.py',b,'layers')
for b in range(6):work(f'E5_ablation_{b}','fusion.py',b)
for b in range(4):work(f'E5_workspace_{b}','workspace_controls.py',b)
for b in range(3):work(f'E5_lifetime_{b}','lifetime.py',b)
work('E6_profiles','profiles.py')
write(runroot()/'GPU_EXECUTION_COMPLETE.json',dict(completed_at=utc(),status='COMPLETE_WITH_RECORDED_NA',required_final_reports_pending=True))
print('GPU_EXECUTION_COMPLETE',flush=True)
