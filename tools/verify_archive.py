#!/usr/bin/env python3
"""Verify release bytes and every archived member. Never execute archived code."""
import argparse, hashlib, json, os, subprocess, tarfile, tempfile
from pathlib import Path, PurePosixPath
ROOT=Path(__file__).resolve().parents[1]
def digest_file(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(4*1024**2),b''):h.update(b)
 return h.hexdigest()
def safe_rel(name):
 p=PurePosixPath(name)
 if p.is_absolute() or '..' in p.parts or not p.parts:raise ValueError('Unsafe archive path: '+name)
 return p

def main():
 a=argparse.ArgumentParser();a.add_argument('--assets',type=Path,required=True);a.add_argument('--extract',type=Path);a.add_argument('--only',help='Archive asset name, including .tar.zst');a.add_argument('--output',type=Path);a.add_argument('--index',type=Path,help='Alternate index for an in-progress archival verification')
 args=a.parse_args();index=json.loads((args.index or ROOT/'archive/INDEX.json').read_text());results=[]
 for record in index['archives']:
  if args.only and record['asset']!=args.only:continue
  segments=record.get('parts',[{'asset':record['asset'],'sha256':record['sha256'],'bytes':record['compressed_bytes']}])
  for seg in segments:
   p=args.assets/seg['asset']
   assert p.stat().st_size==seg['bytes'],('size',str(p))
   assert digest_file(p)==seg['sha256'],('compressed hash',str(p))
  expected={r['path']:r for r in map(json.loads,(ROOT/record['manifest']).read_text().splitlines())};seen=set();total=0
  # cat is only used for verified, fixed filenames passed as argv, never shell strings.
  cat=subprocess.Popen(['cat','--',*[str(args.assets/s['asset']) for s in segments]],stdout=subprocess.PIPE)
  proc=subprocess.Popen(['zstd','-q','-d','-c'],stdin=cat.stdout,stdout=subprocess.PIPE);cat.stdout.close()
  with tarfile.open(fileobj=proc.stdout,mode='r|') as tar:
   for member in tar:
    name=member.name;safe_rel(name);assert name in expected and name not in seen,('unexpected or duplicate',name)
    row=expected[name];seen.add(name)
    if member.issym():
     assert row['type']=='symlink' and row['target']==member.linkname,('symlink mismatch',name)
     continue # Symlink targets can be host-specific: do not materialize automatically.
    if member.islnk():
     safe_rel(member.linkname);assert member.linkname in seen,('forward hard link',name)
     target=expected[member.linkname]
     assert row['type']=='file' and row['sha256']==target['sha256'] and row['bytes']==target['bytes'],('hard link mismatch',name)
     if args.extract:
      import shutil
      root=args.extract.resolve();dest=root/Path(*safe_rel(name).parts);dest.parent.mkdir(parents=True,exist_ok=True)
      assert dest.parent.resolve().is_relative_to(root)
      if dest.exists() or dest.is_symlink():raise FileExistsError(str(dest))
      shutil.copy2(root/Path(*safe_rel(member.linkname).parts),dest)
     total+=row['bytes'];continue
    assert member.isfile() and row['type']=='file' and member.size==row['bytes'],('type/size',name)
    h=hashlib.sha256();f=tar.extractfile(member);dest=None;temp=None
    if args.extract:
     root=args.extract.resolve();dest=root/Path(*safe_rel(name).parts);dest.parent.mkdir(parents=True,exist_ok=True)
     assert dest.parent.resolve().is_relative_to(root),('escape',name)
     if dest.exists() or dest.is_symlink():raise FileExistsError('Use an empty destination: '+str(dest))
     temp=dest.with_name(dest.name+'.verifying');out=temp.open('xb')
    try:
     for b in iter(lambda:f.read(4*1024**2),b''):
      h.update(b)
      if args.extract:out.write(b)
    finally:
     if args.extract:out.close()
    assert h.hexdigest()==row['sha256'],('member hash',name)
    if args.extract:
     os.chmod(temp,row['mode']&0o777);os.utime(temp,ns=(row['mtime_ns'],row['mtime_ns']));temp.rename(dest)
    total+=member.size
  # Drain any tar padding before waiting, avoiding a decompressor pipe deadlock.
  while proc.stdout.read(1024**2):pass
  assert proc.wait()==0 and cat.wait()==0
  assert seen==set(expected),('missing members',record['asset'])
  result={'asset':record['asset'],'members':len(seen),'bytes':total,'verified':True};results.append(result);print(json.dumps(result),flush=True)
 for extra in index.get('additional_assets',[]):
  if args.only:continue
  p=args.assets/extra['asset'];assert p.stat().st_size==extra['bytes'] and digest_file(p)==extra['sha256']
 if args.only and not results:raise ValueError('Unknown --only asset')
 summary={'archives_verified':len(results),'members_verified':sum(x['members'] for x in results),'source_bytes_verified':sum(x['bytes'] for x in results),'results':results,'gpu_experiments_run':0}
 if args.output:args.output.write_text(json.dumps(summary,indent=2)+'\n')
 print(json.dumps({k:v for k,v in summary.items() if k!='results'}),flush=True)
if __name__=='__main__':main()
