#!/usr/bin/env python3
"""Lossless, read-only snapshot of all experiment records; no GPU execution."""
import os, sys, json, hashlib, tarfile, subprocess, shutil, stat, datetime
from pathlib import Path
SRC=Path('/home/ubuntu/文档/ChatGPT/numa_gpu')
REPO=Path('/home/ubuntu/文档/ChatGPT/EXP_NUMA_SM')
OUT=Path(__file__).resolve().parent
ARCH=OUT/'release-assets'; ARCH.mkdir(exist_ok=True)
MAN=REPO/'archive/manifests'; MAN.mkdir(parents=True,exist_ok=True)
EXCLUDED={'.git','__pycache__','.pytest_cache','.mypy_cache','.venv'}
BULK={'runs','raw','data','build','assets','exports','vendor','sources'}
EXT={'.md','.json','.jsonl','.csv','.txt','.yaml','.yml','.toml','.py','.cu','.cuh','.h','.hpp','.cpp','.c','.sh','.patch','.diff','.cmake','.in','.rst','.log','.png','.pdf','.svg','.html'}
def walk(p):
 if p.is_file() or p.is_symlink():return [p]
 result=[]
 for base,ds,fs in os.walk(p,followlinks=False):
  ds[:]=sorted(x for x in ds if x not in EXCLUDED)
  for d in ds[:]:
   q=Path(base)/d
   if q.is_symlink():result.append(q);ds.remove(d)
  result.extend(Path(base)/f for f in sorted(fs) if not f.endswith('.pyc'))
 return sorted(result)
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(4*2**20),b''):h.update(b)
 return h.hexdigest()
def include_git(rel,p):
 if p.is_symlink():return False
 if any(x in BULK for x in rel.parts):return False
 return (p.suffix.lower() in EXT or p.name in ['.gitignore','Makefile','CMakeLists.txt','LICENSE','COPYING']) and p.stat().st_size<8*2**20
# Exact original Git staged state is retained independently; no original commit rewritten.
groups=[]
roots=[]
for p in sorted(SRC.iterdir()):
 if p.name in EXCLUDED:continue
 if p.is_dir():groups.append((p.name,[(x,Path('numa_gpu')/x.relative_to(SRC)) for x in walk(p)],True))
 else:roots.append((p,Path('numa_gpu')/p.name))
groups.insert(0,('root',roots,True))
# Original incoming/outgoing handoff packages and desktop materials, not unrelated personal files.
down=Path('/home/ubuntu/下载')
files=[p for p in down.iterdir() if p.is_file() and any(s in p.name for s in ['T10','GPU','NUMA','FUSED'])]
groups.append(('handoff-downloads',[(p,Path('handoffs/downloads')/p.name) for p in sorted(files)],False))
desk=Path('/home/ubuntu/桌面/GPU双卡拓扑实验_交付_20261014')
groups.append(('handoff-desktop',[(p,Path('handoffs/desktop')/p.relative_to(desk)) for p in walk(desk)],False))
index=[]
for name,files,from_ws in groups:
 dest=ARCH/(name+'.tar.zst'); mf=MAN/(name+'.jsonl')
 if dest.exists() and mf.exists() and (OUT/(name+'.done.json')).exists():
  info=json.loads((OUT/(name+'.done.json')).read_text());index.append(info);print('RESUME',name,flush=True);continue
 print('START',name,len(files),flush=True)
 rows=[];total=0;copied=0;members=[]
 for p,arc in files:
  s=p.lstat();row={'path':arc.as_posix(),'bytes':s.st_size,'mtime_ns':s.st_mtime_ns,'mode':stat.S_IMODE(s.st_mode)}
  if p.is_symlink():row.update(type='symlink',target=os.readlink(p))
  else:row.update(type='file',sha256=digest(p));total+=s.st_size
  if from_ws and include_git(p.relative_to(SRC),p):
   q=REPO/'experiments'/p.relative_to(SRC);q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q);row['git_path']=q.relative_to(REPO).as_posix();copied+=1
  rows.append(row);members.append((p,arc))
 mf.write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in rows))
 with dest.with_suffix('.partial').open('wb') as out:
  proc=subprocess.Popen(['zstd','-6','-T2','-q','-c'],stdin=subprocess.PIPE,stdout=out)
  with tarfile.open(fileobj=proc.stdin,mode='w|',format=tarfile.PAX_FORMAT) as tar:
   for p,arc in members:tar.add(p,arcname=arc.as_posix(),recursive=False)
  proc.stdin.close()
  if proc.wait()!=0:raise RuntimeError('zstd failed')
 dest.with_suffix('.partial').rename(dest)
 info={'asset':dest.name,'manifest':mf.relative_to(REPO).as_posix(),'files':len(files),'source_bytes':total,'compressed_bytes':dest.stat().st_size,'sha256':digest(dest),'git_files':copied}
 (OUT/(name+'.done.json')).write_text(json.dumps(info,indent=2))
 index.append(info);print('DONE',json.dumps(info),flush=True)
index_obj={'snapshot_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_root':str(SRC),'destination':'https://github.com/BorderRegion/EXP_NUMA_SM','release_tag':'records-2026-10-18','archives':index,'exclusions':['Git internals (history is exported separately)','Python bytecode and regenerable interpreter/test caches','unrelated files outside explicit experiment paths'],'total_entries':sum(x['files'] for x in index),'total_source_bytes':sum(x['source_bytes'] for x in index),'total_archive_bytes':sum(x['compressed_bytes'] for x in index),'git_evidence_files':sum(x['git_files'] for x in index)}
(REPO/'archive/INDEX.json').write_text(json.dumps(index_obj,ensure_ascii=False,indent=2)+'\n')
(ARCH/'SHA256SUMS').write_text(''.join(f"{x['sha256']}  {x['asset']}\n" for x in index))
shutil.copy2(ARCH/'SHA256SUMS',REPO/'archive/SHA256SUMS')
print('FINISHED',json.dumps({k:v for k,v in index_obj.items() if k!='archives'}),flush=True)
