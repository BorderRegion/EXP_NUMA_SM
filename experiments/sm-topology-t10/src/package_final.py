from pathlib import Path
import hashlib,json,zipfile,subprocess,tempfile,time,os
R=Path(__file__).resolve().parents[1];dest=Path('/home/ubuntu/下载');stem='T10_SM_TOPOLOGY_AND_OPTIMIZATION_20261017';full=dest/(stem+'.zip');small=dest/(stem+'_SMALL.zip')
assert not full.exists() and not small.exists(),'Never overwrite a delivered archive'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
files=sorted(p for p in R.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc' and p.name not in ['PACKAGE_QA.json','PACKAGE_QA.log','DELIVERY_INDEX.md'])
scope='''# Lightweight review package

Contains the full report, all nine figures, frozen protocols and mappings, source code, effective GPU kernel sources/SASS, all per-process matrix means and comparison results, and reusable schedule model. It omits raw records.bin, raw epochs.csv, last downloaded buffers, historical logs and compiled executables. It is for web GPT/reviewer inspection, not standalone raw-data recomputation. The companion full ZIP contains all raw data and the CPU-only recomputation command.

Main findings: stable address-conditioned empirical SM communication;34/22 address-affinity preference; no recovered physical floorplan. Final synthetic communication time reduction2.458% vs fixed pairing,1.101% vs random,0.478% vs address-blind minimax, six fresh processes. Every negative condition and earlier failed prototype remain in the report/results. Setup and real application are outside the performance scope.
'''
def pack(path,chosen,light=False):
 prefix=path.stem;manifest={str(p.relative_to(R)):dict(sha256=sha(p),bytes=p.stat().st_size) for p in chosen}
 with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for p in chosen:z.write(p,prefix+'/'+str(p.relative_to(R)))
  if light:z.writestr(prefix+'/LIGHT_PACKAGE_SCOPE.md',scope);manifest['LIGHT_PACKAGE_SCOPE.md']=dict(sha256=hashlib.sha256(scope.encode()).hexdigest(),bytes=len(scope.encode()))
  z.writestr(prefix+'/MANIFEST_SHA256.json',json.dumps(manifest,indent=2))
 with zipfile.ZipFile(path) as z:
  assert z.testzip() is None
  for rel,m in manifest.items():assert hashlib.sha256(z.read(prefix+'/'+rel)).hexdigest()==m['sha256']
 digest=sha(path);path.with_suffix(path.suffix+'.sha256').write_text(digest+'  '+path.name+'\n');return dict(path=str(path),bytes=path.stat().st_size,sha256=digest,manifest_entries=len(manifest),crc='PASS',hashes='PASS')
fullmeta=pack(full,files)
chosen=[]
for p in files:
 rel=p.relative_to(R)
 if rel.parts[0] in ['reports','freeze','src','derived'] and p.suffix in ['.md','.json','.png','.pdf','.py','.cu','.cpp','.hpp','.csv','.npz']:chosen.append(p)
 elif rel.parts[0] in ['build','build_v2','build_v3'] and (p.suffix in ['.cu','.hpp'] or p.name.endswith('.sass.txt')):chosen.append(p)
 elif rel.parts[0]=='plans' and p.name.startswith('frozen_maps'):chosen.append(p)
 elif len(rel.parts)==1 and p.suffix in ['.md','.json']:chosen.append(p)
smallmeta=pack(small,chosen,True)
qa=Path(tempfile.mkdtemp(prefix='t10-topology-final-qa-'));start=time.monotonic()
with zipfile.ZipFile(full) as z:z.extractall(qa)
extracted=qa/full.stem;env=os.environ.copy();env['CUDA_VISIBLE_DEVICES']='';env['OMP_NUM_THREADS']='1';env['PYTHONDONTWRITEBYTECODE']='1'
p=subprocess.run(['/home/ubuntu/projects/leetgpu-lab/.venv/bin/python3',str(extracted/'src/recompute.py')],cwd=extracted,env=env,capture_output=True,text=True)
(R/'reports/PACKAGE_QA.log').write_text(p.stdout+p.stderr)
result=dict(full=fullmeta,small=smallmeta,extracted_directory=str(extracted),CPU_only_returncode=p.returncode,CPU_only_stdout=p.stdout,elapsed_seconds=time.monotonic()-start,status='PASS' if p.returncode==0 else 'FAIL')
(R/'reports/PACKAGE_QA.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n');print(json.dumps(result,indent=2,ensure_ascii=False))
if p.returncode:raise SystemExit(p.returncode)
