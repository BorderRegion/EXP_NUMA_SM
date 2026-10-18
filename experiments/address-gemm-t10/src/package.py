from common import *
import zipfile,tempfile,subprocess,time,shutil

def make_zip(name,selected):
 path=Path('/home/ubuntu/下载')/(name+'.zip');manifest={str(p.relative_to(ROOT)):sha(p) for p in selected};name_root=name
 with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p in selected:z.write(p,name_root+'/'+str(p.relative_to(ROOT)))
  z.writestr(name_root+'/MANIFEST_SHA256.json',json.dumps(manifest,indent=2)+'\n')
 with zipfile.ZipFile(path) as z:
  assert z.testzip() is None
  for rel,dig in manifest.items():assert hashlib.sha256(z.read(name_root+'/'+rel)).hexdigest()==dig
 return dict(path=str(path),bytes=path.stat().st_size,sha256=sha(path),manifest_entries=len(manifest),crc='PASS',hashes='PASS')

def main():
 excluded={'MANIFEST_SHA256.json','PACKAGE_QA.json','PACKAGE_QA.log','DELIVERY_INDEX.md'}
 allfiles=sorted(p for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name not in excluded)
 full=make_zip('T10_ADDRESS_AWARE_GEMM_20261017',allfiles)
 smallfiles=[p for p in allfiles if p.relative_to(ROOT).parts[0] in ['src','adapters','reports','derived'] or p.name in ['README.md','STATUS.md','PROTOCOL.json','BEGIN_EXECUTION.json','ORIGIN.json','OFFICIAL_REFERENCES.json']]
 small=make_zip('T10_ADDRESS_AWARE_GEMM_20261017_SMALL',smallfiles)
 parent=Path(tempfile.mkdtemp(prefix='t10-address-gemm-qa-'))
 with zipfile.ZipFile(full['path']) as z:z.extractall(parent)
 extracted=parent/Path(full['path']).stem;t=time.monotonic();p=subprocess.run([PYTHON,str(extracted/'src/recompute.py')],capture_output=True,text=True)
 (ROOT/'reports/PACKAGE_QA.log').write_text(p.stdout+p.stderr)
 assert p.returncode==0,p.stderr
 manifest=read(extracted/'MANIFEST_SHA256.json')
 for rel,dig in manifest.items():assert sha(extracted/rel)==dig,rel
 # Recompute is deterministic: all delivered files still match after its writes.
 qa=dict(status='PASS',full=full,small=small,extracted_directory=str(extracted),CPU_only_returncode=p.returncode,CPU_only_seconds=time.monotonic()-t,CPU_only_stdout_last=p.stdout.splitlines()[-1],post_recompute_all_hashes='PASS')
 write(ROOT/'reports/PACKAGE_QA.json',qa)
 index=f'''# Delivery index — 2026-10-17

Complete real-GEMM experiment; no net speedup versus original CUTLASS.

- Report: `ADDRESS_GEMM_REPORT.md`
- Full: `{full['path']}` — {full['bytes']:,} bytes; {full['manifest_entries']} hash entries.
- Review-only small: `{small['path']}` — {small['bytes']:,} bytes; excludes raw measurements and GPU binaries; cannot independently recompute.
- Full SHA256: `{full['sha256']}`
- Small SHA256: `{small['sha256']}`
- ZIP CRC and all hashes PASS. Fresh extraction CPU recomputation PASS; all delivered hashes remain unchanged after recomputation.
- QA details: `PACKAGE_QA.json`, `PACKAGE_QA.log`.
'''
 (ROOT/'reports/DELIVERY_INDEX.md').write_text(index);print(json.dumps(qa,indent=2))
if __name__=='__main__':main()
