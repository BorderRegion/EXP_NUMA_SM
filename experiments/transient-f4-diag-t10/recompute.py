"""Portable CPU-only evidence check. Never imports CUDA/Torch or runs GPU work."""
from pathlib import Path
import sys,json,hashlib,math,subprocess,os
root=Path(__file__).resolve().parent
manifest=json.loads((root/'MANIFEST_SHA256.json').read_text())
for name,digest in manifest.items():
 p=root/name
 if hashlib.sha256(p.read_bytes()).hexdigest()!=digest:raise RuntimeError('MANIFEST_MISMATCH '+name)
print('MANIFEST_PASS',len(manifest),flush=True)
run=root/'runs'/Path((root/'CURRENT_RUN.txt').read_text().strip()).name
targets=['old_forensics.json','diagnostic_results.json','profile_activity.json']
before={n:json.loads((run/'derived'/n).read_text()) for n in targets}
def compare(a,b,path='root'):
 if isinstance(a,dict):
  assert isinstance(b,dict) and a.keys()==b.keys(),path
  for k in a:compare(a[k],b[k],path+'.'+k)
 elif isinstance(a,list):
  assert isinstance(b,list) and len(a)==len(b),path
  for i,(x,y) in enumerate(zip(a,b)):compare(x,y,path+f'[{i}]')
 elif isinstance(a,(int,float)) and not isinstance(a,bool):assert math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-7),(path,a,b)
 else:assert a==b,(path,a,b)
env=dict(os.environ,OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',MKL_NUM_THREADS='2',PYTHONDONTWRITEBYTECODE='1')
for command in [['forensics.py','--portable'],['analyze_diag.py'],['analyze_profiles.py']]:
 p=subprocess.run([sys.executable,str(root/'src'/command[0]),*command[1:]],cwd=root,env=env,capture_output=True,text=True)
 print(command[0],p.returncode,p.stdout[-1000:],flush=True)
 if p.returncode:print(p.stderr);raise SystemExit(p.returncode)
for n in targets:compare(before[n],json.loads((run/'derived'/n).read_text()))
print('ALL_DERIVED_RECOMPUTATION_PASS',flush=True)
assert not any(x in sys.modules for x in ['torch','cuda'])
print('CPU_ONLY_PASS_NO_GPU_RERUN',flush=True)
