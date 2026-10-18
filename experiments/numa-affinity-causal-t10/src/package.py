from common import *
import os,zipfile,subprocess,tempfile,shutil
EXCLUDED={'reports/DELIVERY_INDEX.md','reports/PACKAGE_QA.json','reports/CPU_RECOMPUTE_QA.log'}
def included(p):return p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc' and str(p.relative_to(ROOT)) not in EXCLUDED and p.relative_to(ROOT).parts[0]!='qa'
def pack(path,files):
 entries={str(p.relative_to(ROOT)):dict(bytes=p.stat().st_size,sha256=sha(p)) for p in files}
 with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p in files:z.write(p,ROOT.name+'/'+str(p.relative_to(ROOT)))
  z.writestr('MANIFEST.json',json.dumps(dict(root=ROOT.name,files=entries),ensure_ascii=False,indent=2)+'\n')
 with zipfile.ZipFile(path) as z:
  assert z.testzip() is None
  for rel,e in entries.items():
   b=z.read(ROOT.name+'/'+rel);assert len(b)==e['bytes'] and hashlib.sha256(b).hexdigest()==e['sha256']
 return dict(path=str(path),bytes=path.stat().st_size,sha256=sha(path),files=len(entries))
def main():
 assert read(ROOT/'derived/AUDIT.json')['status']=='PASS';files=sorted(p for p in ROOT.rglob('*') if included(p));out=Path('/home/ubuntu/下载');full=out/'T10_AFFINITY_CAUSAL_20261018.zip';small=out/'T10_AFFINITY_CAUSAL_20261018_SMALL.zip';assert not full.exists() and not small.exists()
 fm=pack(full,files);keep=[]
 for p in files:
  rel=p.relative_to(ROOT)
  if rel.parts[0] in ['src','freeze','reports'] or rel.name in ['CURRENT_RUN.txt','README_REPRODUCE.md'] or str(rel) in ['derived/AUDIT.json','derived/DECISION.json','derived/INSTRUCTION_AUDIT.json','support/runtime_versions.json','support/environment.json'] or rel.parts[0]=='build' and p.suffix in ['.json','.log']:keep.append(p)
 sm=pack(small,keep);qa=Path(tempfile.mkdtemp(prefix='t10_causal_cpu_qa_'));log=ROOT/'reports/CPU_RECOMPUTE_QA.log'
 try:
  with zipfile.ZipFile(full) as z:z.extractall(qa);manifest=json.loads(z.read('MANIFEST.json'))
  env=os.environ.copy();env.update(CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='2',OMP_NUM_THREADS='2')
  with log.open('w') as f:
   for script in ['recompute.py','stability.py']:
    p=subprocess.run([PYTHON,str(qa/ROOT.name/'src'/script)],stdout=f,stderr=subprocess.STDOUT,env=env,timeout=300);assert p.returncode==0,(script,str(log))
  for rel,e in manifest['files'].items():assert sha(qa/ROOT.name/rel)==e['sha256'],('recompute changed artifact',rel)
  result=dict(status='PASS',created_utc=utc(),full=fm,small=sm,crc_and_sha256='PASS',independent_extraction_cpu_recompute='PASS',packaged_files_unchanged=True)
  write(ROOT/'reports/PACKAGE_QA.json',result)
  (ROOT/'reports/DELIVERY_INDEX.md').write_text(f"# 交付索引\n\n- [报告](REPORT.md)\n- [质疑清单](REVIEW_QUESTIONS.md)\n- [完整包]({full})，{fm['bytes']} bytes，{fm['files']}项，SHA256 `{fm['sha256']}`\n- [网页版GPT小包]({small})，{sm['bytes']} bytes，{sm['files']}项，SHA256 `{sm['sha256']}`\n\nCRC、逐文件SHA256、完整包独立解压纯CPU复算通过，复算后文件哈希不变。小包省略原始计时和二进制，不宣称可独立完整复算。\n")
  print(json.dumps(result,ensure_ascii=False,indent=2))
 finally:shutil.rmtree(qa)
if __name__=='__main__':main()
