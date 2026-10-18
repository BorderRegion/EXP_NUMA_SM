"""Freeze local source and inputs before launching a future GPU worker.

Installed CUDA/PyTorch libraries remain external and retain their separate locks.
This helper does not acquire a GPU or invoke a subprocess itself.
"""
import hashlib
import json
import os
from pathlib import Path

SOURCE_DIRS = ('tools','src','include','config','preregistration','protocol','vendor',
               'recovery_20261015/include','recovery_20261015/tools',
               'recovery_20261015/config')
SKIP = {'__pycache__','.git','build','.pytest_cache'}

def freeze(root, entry, destination):
    root,entry,destination=map(lambda p:Path(p).resolve(),(root,entry,destination))
    relative=entry.relative_to(root)
    destination.mkdir(parents=True,exist_ok=False)
    records=[]
    for directory in SOURCE_DIRS:
        source=root/directory
        if not source.exists(): continue
        for parent,dirs,files in os.walk(source):
            for name in dirs:
                if (Path(parent)/name).is_symlink():
                    raise ValueError('Source directory symlink requires explicit vendoring: '+str(Path(parent)/name))
            dirs[:]=sorted(d for d in dirs if d not in SKIP)
            # Keep all compiled CUTLASS headers, utilities and source identity;
            # non-executable manuals/media and the Git database are not runtime dependencies.
            rel_parent=Path(parent).relative_to(root).as_posix()
            if rel_parent=='vendor': dirs[:]=[d for d in dirs if d=='cutlass'];files=[]
            elif rel_parent=='vendor/cutlass':
                dirs[:]=[d for d in dirs if d in ('include','tools')]
                files=[n for n in files if n in ('LICENSE.txt','SOURCE_ID.json')]
            elif rel_parent=='vendor/cutlass/tools': dirs[:]=[d for d in dirs if d=='util'];files=[]
            elif rel_parent=='vendor/cutlass/tools/util': dirs[:]=[d for d in dirs if d=='include'];files=[]
            for name in sorted(files):
                p=Path(parent)/name
                if p.is_symlink(): raise ValueError('Source file symlink requires explicit vendoring: '+str(p))
                rel=p.relative_to(root)
                data=p.read_bytes();target=destination/rel
                target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(data)
                target.chmod(0o555 if os.access(p,os.X_OK) else 0o444)
                records.append(dict(path=str(rel),sha256=hashlib.sha256(data).hexdigest(),bytes=len(data)))
    if not (destination/relative).is_file():
        raise ValueError('Entry is outside the frozen source directories')
    # Fail closed if anything changed during the copy window.
    for record in records:
        if hashlib.sha256((root/record['path']).read_bytes()).hexdigest()!=record['sha256']:
            raise RuntimeError('Source changed while freezing: '+record['path'])
    manifest=destination/'FROZEN_SOURCE_MANIFEST.json'
    manifest.write_text(json.dumps(records,indent=2)+'\n');manifest.chmod(0o444)
    for parent,dirs,files in os.walk(destination,topdown=False): Path(parent).chmod(0o555)
    return destination/relative, records
