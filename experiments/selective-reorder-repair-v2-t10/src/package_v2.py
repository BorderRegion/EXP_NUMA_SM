from common import *
import zipfile,sys
rootname='T10_SELECTIVE_REORDER_REPAIR_V2_RESULT_20261017';dest=Path('/home/ubuntu/下载')/(rootname+'.zip');run=runroot();paths=[]
allowed={'src','adapters','patches','freeze','input','reference','support','reports','build'}
for p in ROOT.rglob('*'):
 if not p.is_file():continue
 rel=p.relative_to(ROOT)
 if '__pycache__' in rel.parts or p.suffix in ['.pyc','.o']:continue
 if rel.parts[0]=='runs' and run.name not in rel.parts:continue
 if rel.parts[0] not in allowed|{'runs'} and len(rel.parts)!=1:continue
 if p.name in ['PACKAGE_QA.json','PACKAGE_QA.log','DELIVERY.json','MANIFEST_SHA256.json'] or 'fresh_recompute' in rel.parts:continue
 if p.suffix=='.sass':continue  # Cubin hashes and unchanged source prove identity; avoid duplicate disassembly.
 if p.suffix=='.cubin' and p.parent!=Path((ROOT/'BUILD.txt').read_text().strip()):continue
 paths.append(p)
manifest={str(p.relative_to(ROOT)):sha(p) for p in sorted(paths)};write(ROOT/'MANIFEST_SHA256.json',manifest);paths.append(ROOT/'MANIFEST_SHA256.json')
with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 for p in sorted(paths):z.write(p,rootname+'/'+str(p.relative_to(ROOT)))
assert zipfile.ZipFile(dest).testzip() is None
info=dict(path=str(dest),files=len(paths),bytes=dest.stat().st_size,sha256=sha(dest),created_at=utc());write(ROOT/'reports/DELIVERY.json',info);dest.with_suffix('.zip.sha256').write_text(info['sha256']+'  '+dest.name+'\n');print(json.dumps(info,indent=2))
