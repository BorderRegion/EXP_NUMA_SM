"""Offline CPU-only reconstruction; no Torch/CUDA imported or GPU run."""
from pathlib import Path
import sys,os,json,hashlib,math,subprocess
root=Path(__file__).resolve().parent
manifest=json.loads((root/'MANIFEST_SHA256.json').read_text())
for n,d in manifest.items():assert hashlib.sha256((root/n).read_bytes()).hexdigest()==d,n
print('MANIFEST_PASS',len(manifest),flush=True)
r=root/'runs'/Path((root/'CURRENT_RUN.txt').read_text().strip()).name
before={n:json.loads((r/'derived'/n).read_text()) for n in ['results.json','profiles.json']}
def compare(a,b,path='root'):
 if isinstance(a,dict):
  assert a.keys()==b.keys(),path
  for k in a:compare(a[k],b[k],path+'.'+k)
 elif isinstance(a,list):
  assert len(a)==len(b),path
  for i,(x,y) in enumerate(zip(a,b)):compare(x,y,path+f'[{i}]')
 elif isinstance(a,(int,float)) and not isinstance(a,bool):assert math.isclose(a,b,abs_tol=1e-7,rel_tol=1e-10),(path,a,b)
 else:assert a==b,(path,a,b)
env=dict(os.environ,CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',MKL_NUM_THREADS='2')
for script in ['analyze.py','analyze_profiles.py']:
 p=subprocess.run([sys.executable,str(root/'src'/script)],cwd=root,env=env,capture_output=True,text=True);print(script,p.returncode,p.stdout[-1200:],flush=True)
 if p.returncode:print(p.stderr);raise SystemExit(p.returncode)
for n,x in before.items():compare(x,json.loads((r/'derived'/n).read_text()))
print('ALL_DERIVED_RECOMPUTATION_PASS',flush=True)
