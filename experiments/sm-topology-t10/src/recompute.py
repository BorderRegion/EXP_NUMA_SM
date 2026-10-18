from pathlib import Path
import subprocess,sys,tempfile,json,math,shutil,numpy as np
root=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='topology-derived-') as temp:
 out=Path(temp);subprocess.run([sys.executable,str(root/'src/analyze_final.py'),'--root',str(root),'--out',str(out)],check=True,stdout=subprocess.DEVNULL)
 def equal(a,b,path=''):
  if isinstance(a,dict):
   assert a.keys()==b.keys(),path
   for k in a:equal(a[k],b[k],path+'/'+k)
  elif isinstance(a,list):
   assert len(a)==len(b),path
   for i,(x,y) in enumerate(zip(a,b)):equal(x,y,path+'/'+str(i))
  elif isinstance(a,float):assert math.isclose(a,b,rel_tol=1e-11,abs_tol=1e-8),(path,a,b)
  else:assert a==b,(path,a,b)
 for f in ['RESULTS.json','AUDIT.json','DEPLOYMENT_PHASES.json','ROW_COLUMN_COMPONENTS.json']:equal(json.loads((root/'derived'/f).read_text()),json.loads((out/f).read_text()),f)
 for f in ['pair_matrix.csv','address_matrix.csv','address_conditioned_tensor.csv']:assert (root/'derived'/f).read_bytes()==(out/f).read_bytes(),f
 for f in ['matrices.npz','address_conditioned_tensor.npz']:
  a=np.load(root/'derived'/f);b=np.load(out/f);assert set(a.files)==set(b.files)
  for k in a.files:assert np.allclose(a[k],b[k],rtol=1e-11,atol=1e-8),f+'/'+k
 from compile_topology_schedule import compile_schedule
 model=json.loads((root/'derived/TOPOLOGY_MODEL.json').read_text())
 for page in [0,17,257]:
  for objective in ['minimax','sum']:equal(compile_schedule(model,page,objective),json.loads((root/f'derived/SCHEDULE_page{page}_{objective}.json').read_text()))
print('ALL_RAW_DERIVATIONS_AND_FROZEN_SCHEDULES_RECOMPUTED_PASS')
