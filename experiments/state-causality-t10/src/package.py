from common import *
import zipfile
name='T10_STATE_CAUSALITY_RESULT_20261017';dest=Path('/home/ubuntu/下载')/(name+'.zip');files={}
for dirname in ['src','adapters','freeze','support','reports','runs','build']:
 for p in (ROOT/dirname).rglob('*'):
  if not p.is_file() or '__pycache__' in p.parts or p.suffix in ['.pyc','.o','.sass']:continue
  if p.name in ['DELIVERY.json','DELIVERY_INDEX.md','PACKAGE_QA.json','PACKAGE_QA.log']:continue
  files[str(p.relative_to(ROOT))]=p
for n in ['BEGIN_EXECUTION.json','END_EXECUTION.json','CURRENT_RUN.txt','BUILD.txt','STATUS.md','README_REPRODUCE.md','recompute.py']:
 if (ROOT/n).exists():files[n]=ROOT/n
write(ROOT/'MANIFEST_SHA256.json',{n:sha(p) for n,p in files.items()});files['MANIFEST_SHA256.json']=ROOT/'MANIFEST_SHA256.json'
if dest.exists():dest.rename(dest.with_name(dest.stem+'.previous_'+str(time.time_ns())+'.zip'))
with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 for n,p in sorted(files.items()):z.write(p,name+'/'+n)
with zipfile.ZipFile(dest) as z:assert z.testzip() is None
res=dict(path=str(dest),bytes=dest.stat().st_size,sha256=sha(dest),files=len(files),at=utc());write(ROOT/'reports/DELIVERY.json',res);dest.with_suffix('.zip.sha256').write_text(res['sha256']+'  '+dest.name+'\n');print(json.dumps(res,ensure_ascii=False))
