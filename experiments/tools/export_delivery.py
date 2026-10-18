#!/usr/bin/env python3
"""Deterministic evidence selection; normalize host paths without changing raw CSV."""
import pathlib,json,hashlib,shutil,re,datetime
ROOT=pathlib.Path(__file__).resolve().parents[1];DEST=ROOT/'exports/GPU_TOPOLOGY_T10_20261014'
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 if DEST.exists():raise SystemExit('Export already exists; retain it and choose a fresh destination')
 DEST.mkdir(parents=True);paths=set();large=[]
 def addtree(p):
  for f in p.rglob('*'):
   if f.is_file()and not f.is_symlink()and '.git'not in f.parts and '__pycache__'not in f.parts and f.suffix!='.pyc':paths.add(f)
 for name in ['src','tools','GPU_COMPUTE_TOPOLOGY_DUAL_20261014','preregistration','derived','reports','environment','build']:addtree(ROOT/name)
 paths={p for p in paths if p.name not in ['gpu_worker.lock','qa_montage.png']and not any(x in p.parts for x in ['current','renderer_current','sparse_current'])}
 for name in ['STATUS.md','WORKLOG.md','DECISIONS.jsonl','LOCAL_RESOURCE_GAPS.md','run_index.jsonl','REPRODUCE.md','SOURCE_LOCKS.json']:paths.add(ROOT/name)
 for name in ['diff-gaussian-rasterization','cub','thrust']:addtree(ROOT/'vendor'/name)
 addtree(ROOT/'vendor/CUDALibrarySamples/cuSPARSE/spmv_csr')
 for p in (ROOT/'vendor/CUDALibrarySamples').glob('*LICENSE*'):paths.add(p)
 for p in (ROOT/'assets').rglob('*'):
  if p.is_file()and(p.suffix in ['.json','.jsonl']or p.name=='cfg_args'):paths.add(p)
 runs=[json.loads(x)for x in (ROOT/'run_index.jsonl').read_text().splitlines()];selected={}
 for r in sorted(runs,key=lambda r:r['start_utc']):
  if r['stage']in['E4_W1','E4_W2']and r['status']=='SUCCESS':
   c=r['config'];key=(r['stage'],c.get('scene',c.get('input')),c['sequence']);selected.setdefault(key,r['run_id'])
 for r in runs:
  for p in (ROOT/r['path']).iterdir():
   if not p.is_file():continue
   if p.suffix!='.bin' or r['status']=='FAILED' or r['run_id']in selected.values():paths.add(p)
   else:large.append(dict(path=str(p.relative_to(ROOT)),bytes=p.stat().st_size,selection='omitted large output; earliest successful input/sequence run retained'))
 replacements=[(str(ROOT),'${PACKAGE_ROOT}'),('/home/ubuntu/projects/leetgpu-lab','${TOOLCHAIN_ROOT}'),('/home/ubuntu','${USER_HOME}')]
 def norm(s):
  for old,new in replacements:s=s.replace(old,new)
  s=re.sub(r'GPU-[0-9a-fA-F-]{20,}','GPU-REDACTED',s)
  s=re.sub(r'(Serial Number\s*:\s*)[^\n]+',r'\1REDACTED',s)
  return s
 def obj(x):
  if isinstance(x,str):return norm(x)
  if isinstance(x,list):return[obj(y)for y in x]
  if isinstance(x,dict):return{norm(k):obj(v)for k,v in x.items()}
  return x
 entries=[]
 for p in sorted(paths):
  rel=p.relative_to(ROOT);target=DEST/rel;target.parent.mkdir(parents=True,exist_ok=True);raw=p.read_bytes();out=raw
  if p.suffix!='.csv':
   try:
    text=raw.decode('utf8')
    if p.suffix=='.json':
     original=json.loads(text);normalized=obj(original)
     if normalized!=original:out=json.dumps(normalized,indent=2,ensure_ascii=False).encode()
    elif p.suffix=='.jsonl':
     original=[json.loads(line)for line in text.splitlines()];normalized=obj(original)
     if normalized!=original:out=('\n'.join(json.dumps(line,ensure_ascii=False)for line in normalized)+'\n').encode()
    else:out=norm(text).encode()
   except(UnicodeDecodeError,json.JSONDecodeError):pass
  target.write_bytes(out);target.chmod(p.stat().st_mode&0o777)
  entries.append(dict(path=str(rel),bytes=len(out),source_sha256=sha(raw),export_sha256=sha(out),normalized=out!=raw))
 manifest=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),selection_rule='All small CSV/logs, all failures; complete binary output from earliest successful E4 run per input/sequence only',selected_large_output_runs=[dict(stage=k[0],input=k[1],sequence=k[2],run_id=v)for k,v in selected.items()],omitted_large_output_files=large,files=entries)
 (DEST/'EXPORT_MANIFEST.json').write_text(json.dumps(manifest,indent=2));print(DEST);print(len(entries),'files',sum(x['bytes']for x in entries),'bytes')
if __name__=='__main__':main()
