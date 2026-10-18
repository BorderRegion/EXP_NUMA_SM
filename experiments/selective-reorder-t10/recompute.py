#!/usr/bin/env python3
"""Offline CPU verification of this evidence package. Requires Python3 + numpy."""
from pathlib import Path
import sys,json,hashlib,subprocess,tempfile,math
root=Path(__file__).resolve().parent
manifest=json.loads((root/'PACKAGE_MANIFEST.json').read_text())
for name,want in manifest['sha256'].items():
 p=root/name
 if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=want:raise SystemExit('HASH_MISMATCH '+name)
print('MANIFEST_PASS',len(manifest['sha256']))
meta=json.loads((root/'PACKAGE_METADATA.json').read_text());run=root/'runs'/meta['run_id']
def lines(p):return [json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []
sample_checked=0;life_checked=0;tuner_checked=0;action_order=['LIB','SINGLE','SPLIT','PC0_0','PC0_1','PC1_0','PC1_1','PC2_0','PC2_1']
for folder in sorted((run/'raw').iterdir()):
 phases={x['phase_id']:x for x in lines(folder/'phases.jsonl')}
 for row in lines(folder/'samples.jsonl'):
  phase=phases[row['phase_id']]
  for metric in ['cpu_ready_us','gpu_us']:
   observed=sum(x[metric] for x in row['samples'])/len(row['samples']);assert math.isclose(observed,phase[metric],rel_tol=1e-12,abs_tol=1e-8),(folder.name,row['phase_id'],metric)
  sample_checked+=1
 lifecycle={(x['case'],x['policy'],a['H']):a for x in lines(folder/'lifecycle.jsonl') for a in x['records']}
 for row in lines(folder/'lifecycle_samples.jsonl'):
  phase=lifecycle[row['case'],row['policy'],row['H']]['request_result']
  for metric in ['cpu_ready_us','gpu_us']:
   observed=sum(x[metric] for x in row['samples'])/len(row['samples']);assert math.isclose(observed,phase[metric],rel_tol=1e-12,abs_tol=1e-8)
  life_checked+=1
 for row in lines(folder/'tuner_pilots.jsonl'):
  winner=min(row['actions'],key=lambda x:(x['cpu_ready_us'],action_order.index(x['action'])))['action'];assert winner==row['winner'];tuner_checked+=1
print('SAVED_REQUEST_MEANS_PASS',sample_checked,'LIFECYCLE_MEANS_PASS',life_checked,'TUNER_WINNERS_PASS',tuner_checked)
print('KNOWN_LIMITATION: lifecycle blocks0/1 retain complete per-plan means/costs, but their individual request arrays were not stored; no replacement data used.')
with tempfile.TemporaryDirectory(prefix='t10_cpu_recompute_') as td:
 out=Path(td)
 for script in ['analyze.py','supplement.py']:subprocess.run([sys.executable,str(root/'src'/script),str(run),str(out)],check=True)
 checked=[]
 for p in sorted(out.iterdir()):
  q=root/'derived'/p.name
  if not q.exists():raise SystemExit('DERIVED_MISSING '+p.name)
  if p.suffix=='.jsonl':a=[json.loads(x) for x in p.read_text().splitlines()];b=[json.loads(x) for x in q.read_text().splitlines()]
  else:a=json.loads(p.read_text());b=json.loads(q.read_text())
  if p.name=='inventory.json':a.pop('run',None);b.pop('run',None)
  if a!=b:raise SystemExit('RECOMPUTE_MISMATCH '+p.name)
  checked.append(p.name)
 print('STATISTICS_RECOMPUTE_PASS',len(checked))
sys.path.insert(0,str(root/'src'))
from policy_api import py_choice,CPUChooser
cases={x['id']:x for x in json.loads((root/'input/T10_SELECTIVE_REORDER_8H5_20261017/plans/cases.json').read_text())};choices=json.loads((root/'freeze/ALL_CHOICES_BEFORE_TEST.json').read_text());cpu=CPUChooser(root/'build/policy_cpu_final.so')
for row in choices:
 c=cases[row['case']];py=py_choice(c,row['policy'],1024);cpp=cpu.choose(c,row['policy'],1024)
 for k in ['base_action','chosen_action']:
  assert row[k]==py[k]==cpp[k],(row['case'],row['policy'],k)
 if row['predictions'] is not None:
  for a in action_order:assert math.isclose(row['predictions'][a],py['predictions'][a],rel_tol=1e-10,abs_tol=1e-8) and math.isclose(row['predictions'][a],cpp['predictions'][a],rel_tol=1e-10,abs_tol=1e-8)
print('FROZEN_CPU_CHOICE_PASS',len(choices));print('GPU_NOT_USED; statistical and policy verification only, not a rerun of GPU timings.')
