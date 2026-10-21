from pathlib import Path
import json,hashlib,urllib.request,concurrent.futures,tarfile,shutil,time
root=Path(__file__).resolve().parents[1]; inbox=root/'offline_inbox/toolchain'; meta=json.loads((root/'offline_inbox/docs/redistrib_13.2.0.json').read_text())
keys=['cuda_nvcc','cuda_cudart','cuda_crt','cuda_cccl','libnvvm','cuda_cuobjdump','cuda_nvdisasm']
def fetch(key):
    item=meta[key]['linux-x86_64']; url='https://developer.download.nvidia.com/compute/cuda/redist/'+item['relative_path']; dest=inbox/Path(item['relative_path']).name
    start=time.monotonic()
    if not dest.exists():
        temp=dest.with_suffix('.part')
        with urllib.request.urlopen(url,timeout=60) as src,temp.open('wb') as out:shutil.copyfileobj(src,out,1024*1024)
        temp.rename(dest)
    assert dest.stat().st_size==int(item['size'])
    assert hashlib.sha256(dest.read_bytes()).hexdigest()==item['sha256']
    print(key,'verified',dest.stat().st_size,round(time.monotonic()-start,2),flush=True)
    return {'component':key,'version':meta[key]['version'],'url':url,'path':str(dest.relative_to(root)),'bytes':dest.stat().st_size,'sha256':item['sha256']}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:records=list(pool.map(fetch,keys))
packages=inbox/'packages';packages.mkdir(exist_ok=True);prefix=inbox/'cuda-13.2';prefix.mkdir(exist_ok=True)
for item in records:
    with tarfile.open(root/item['path']) as archive:
        members=archive.getmembers();top=members[0].name.split('/')[0]
        archive.extractall(packages,filter='data')
    src=packages/top
    for path in src.iterdir():
        if path.is_dir():shutil.copytree(path,prefix/path.name,dirs_exist_ok=True,symlinks=True)
        else:
            lic=prefix/'component_metadata'/item['component'];lic.mkdir(parents=True,exist_ok=True);shutil.copy2(path,lic/path.name)
(root/'recovery/TOOLCHAIN_LOCK.json').write_text(json.dumps(records,indent=2)+'\n')
(root/'env.sh').write_text('# Workspace-local CUDA environment. Source this file; no system changes.\n'+f'export CUDA_HOME={str(prefix)!r}\nexport PATH="$CUDA_HOME/bin:$PATH"\nexport LD_LIBRARY_PATH="$CUDA_HOME/lib${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}"\n')
print('toolchain_prefix',prefix,flush=True)
