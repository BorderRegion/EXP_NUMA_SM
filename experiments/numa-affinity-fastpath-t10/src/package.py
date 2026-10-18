from common import *
import zipfile,subprocess,os,tempfile,shutil
def excluded(p):
 rel=str(p.relative_to(ROOT));return '__pycache__' in p.parts or p.suffix=='.pyc' or rel in ['reports/DELIVERY_INDEX.md','reports/PACKAGE_QA.json','reports/CPU_RECOMPUTE_QA.log'] or rel.startswith('qa/')
def pack(path,files):
 entries={str(p.relative_to(ROOT)):dict(bytes=p.stat().st_size,sha256=sha(p)) for p in files}
 with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p in files:z.write(p,ROOT.name+'/'+str(p.relative_to(ROOT)))
  z.writestr('MANIFEST.json',json.dumps(dict(root=ROOT.name,files=entries),ensure_ascii=False,indent=2)+'\n')
 with zipfile.ZipFile(path) as z:
  assert z.testzip() is None
  for rel,e in entries.items():
   data=z.read(ROOT.name+'/'+rel);assert len(data)==e['bytes'] and hashlib.sha256(data).hexdigest()==e['sha256']
 return dict(path=str(path),bytes=path.stat().st_size,sha256=sha(path),files=len(entries))
def main():
 assert read(ROOT/'derived/AUDIT.json')['status']=='PASS';files=sorted(p for p in ROOT.rglob('*') if p.is_file() and not excluded(p));download=Path('/home/ubuntu/下载');full=download/'T10_SM_AFFINITY_SOFTMAX_20261018.zip';small=download/'T10_SM_AFFINITY_SOFTMAX_20261018_SMALL.zip';assert not full.exists() and not small.exists()
 full_meta=pack(full,files)
 keep=[]
 for p in files:
  rel=p.relative_to(ROOT)
  if rel.parts[0] in ['src','freeze','reports'] or rel.name in ['README_REPRODUCE.md','CURRENT_RUN.txt'] or str(rel) in ['derived/AUDIT.json','derived/COSTS.json','derived/DEPLOYMENT_GATE.json','derived/INSTRUCTION_AUDIT.json','derived/softmax_topology.json','support/runtime_environment.json'] or rel.parts[0]=='build' and p.suffix in ['.json','.log'] or rel.parts[0]=='support' and p.suffix in ['.patch','.cu']:keep.append(p)
 small_meta=pack(small,keep)
 qa=Path(tempfile.mkdtemp(prefix='t10_affinity_cpu_qa_'));log=ROOT/'reports/CPU_RECOMPUTE_QA.log'
 try:
  with zipfile.ZipFile(full) as z:z.extractall(qa);manifest=json.loads(z.read('MANIFEST.json'))
  env=os.environ.copy();env.update(CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='2',OMP_NUM_THREADS='2')
  with log.open('w') as f:p=subprocess.run([PYTHON,str(qa/ROOT.name/'src/recompute.py')],stdout=f,stderr=subprocess.STDOUT,env=env,timeout=300)
  assert p.returncode==0,log
  for rel,e in manifest['files'].items():assert sha(qa/ROOT.name/rel)==e['sha256'],('recompute mutated artifact',rel)
  result=dict(created_utc=utc(),status='PASS',full=full_meta,small=small_meta,fresh_extraction_cpu_recompute='PASS',packaged_files_unchanged_after_recompute=True,crc_and_all_file_sha256='PASS',qa_log=str(log))
  write(ROOT/'reports/PACKAGE_QA.json',result)
  (ROOT/'reports/DELIVERY_INDEX.md').write_text(f"# 交付索引\n\n- [实验报告](REPORT.md)\n- [紧凑统计结果](RESULTS_COMPACT.json)\n- [完整包]({full})：{full_meta['bytes']} bytes，{full_meta['files']} 项；SHA256 `{full_meta['sha256']}`\n- [网页版 GPT 小包]({small})：{small_meta['bytes']} bytes，{small_meta['files']} 项；SHA256 `{small_meta['sha256']}`\n\nZIP CRC、逐文件 SHA256、全包独立解压纯 CPU 复算通过；复算后包内文件哈希不变。小包省略原始计时和二进制，不宣称能独立完整复算。\n")
  print(json.dumps(result,ensure_ascii=False,indent=2))
 finally:shutil.rmtree(qa)
if __name__=='__main__':main()
