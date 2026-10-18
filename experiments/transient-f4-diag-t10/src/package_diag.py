from common import *
import zipfile
name='T10_TRANSIENT_AND_F4_DIAG_RESULT_20261017';dest=Path('/home/ubuntu/下载')/(name+'.zip')
files={};build=Path((ROOT/'BUILD.txt').read_text().strip())
for directory in ['src','input','input_tools','reference','tests','adapters','patches','freeze','support','reports','runs','build']:
 for p in (ROOT/directory).rglob('*'):
  if not p.is_file() or '__pycache__' in p.parts or p.suffix in ['.pyc','.o','.sass']:continue
  if p.name in ['DELIVERY.json','PACKAGE_QA.json','PACKAGE_QA.log','DELIVERY_INDEX.md']:continue
  if directory=='build' and p.suffix=='.cubin' and p.parent!=build:continue
  files[str(p.relative_to(ROOT))]=p
for n in ['BEGIN_EXECUTION.json','END_EXECUTION.json','CURRENT_RUN.txt','BUILD.txt','STATUS.md','README_REPRODUCE.md','recompute.py']:
 p=ROOT/n
 if p.exists():files[n]=p
manifest={n:sha(p) for n,p in files.items()};write(ROOT/'MANIFEST_SHA256.json',manifest);files['MANIFEST_SHA256.json']=ROOT/'MANIFEST_SHA256.json'
if dest.exists():
 backup=dest.with_name(dest.stem+'.previous_'+str(time.time_ns())+'.zip');dest.rename(backup)
with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 for n,p in sorted(files.items()):z.write(p,name+'/'+n)
with zipfile.ZipFile(dest) as z:assert z.testzip() is None
result=dict(path=str(dest),bytes=dest.stat().st_size,files=len(files),sha256=sha(dest),created_at=utc(),scope='All new raw requests/warmups and profiling; focused prior evidence only; no duplicate entire old run')
write(ROOT/'reports/DELIVERY.json',result);dest.with_suffix('.zip.sha256').write_text(result['sha256']+'  '+dest.name+'\n');print(json.dumps(result,ensure_ascii=False))
