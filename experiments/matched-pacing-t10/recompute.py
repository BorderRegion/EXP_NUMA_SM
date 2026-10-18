"""Portable offline CPU-only raw recomputation. No Torch/CUDA imported."""
from pathlib import Path
import os,sys,json,hashlib,math,subprocess
root=Path(__file__).resolve().parent;manifest=json.loads((root/'MANIFEST_SHA256.json').read_text())
for n,h in manifest.items():assert hashlib.sha256((root/n).read_bytes()).hexdigest()==h,n
print('MANIFEST_PASS',len(manifest),flush=True)
r=root/'runs'/Path((root/'CURRENT_RUN.txt').read_text().strip()).name;before=json.loads((r/'derived/results.json').read_text())
env=dict(os.environ,CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='2',OMP_NUM_THREADS='2',MKL_NUM_THREADS='2')
p=subprocess.run([sys.executable,str(root/'src/analyze_matched.py')],cwd=root,env=env,capture_output=True,text=True);print(p.stdout[-2000:],flush=True)
if p.returncode:print(p.stderr);raise SystemExit(p.returncode)
after=json.loads((r/'derived/results.json').read_text())
def compare(a,b,path='root'):
 if isinstance(a,dict):
  assert a.keys()==b.keys(),path
  for k in a:compare(a[k],b[k],path+'.'+k)
 elif isinstance(a,list):
  assert len(a)==len(b),path
  for i,(x,y) in enumerate(zip(a,b)):compare(x,y,path+f'[{i}]')
 elif isinstance(a,(float,int)) and not isinstance(a,bool):assert math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-7),(path,a,b)
 else:assert a==b,(path,a,b)
compare(before,after);print('ALL_DERIVED_RECOMPUTATION_PASS',flush=True)
