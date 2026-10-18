"""Record and snapshot small external source dependencies; no GPU/network use."""
import importlib.metadata as im
import json, shutil, subprocess, sys
from common import *
r=runroot();dest=r/'compiled/external_sources';dest.mkdir(exist_ok=True)
paths=[REPO/'src/driver_backend.hpp',REPO/'src/render_dispatch.h',REPO/'op-fused/tools/same_q_v2_backend.py',REPO/'op-fused/tools/build_same_q_v2.py',REPO/'op-fused/config/same_q_v2_build_latest.json',REPO/'op-fused/vendor/cutlass/include/cutlass/version.h',Path('/home/ubuntu/projects/leetgpu-lab/lgjudge/cudabuild.py')]
paths += list((REPO/'op-fused/src/same_q_v2').glob('*.h'))+list((REPO/'op-fused/src/same_q_v2').glob('*.cu'))
rows=[]
for p in paths:
 assert p.is_file(),p
 name=str(p.relative_to(REPO)).replace('/','__') if p.is_relative_to(REPO) else 'leetgpu__cudabuild.py'
 shutil.copy2(p,dest/name);rows.append(dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p),snapshot=str((dest/name).relative_to(r))))
binary=REPO/'op-fused/src/same_q_v2/libopf_grouped.so'
versions={}
for package in ['torch','numpy','matplotlib','nvidia-cublas-cu12','nvidia-cusparse-cu12','nvidia-cuda-runtime-cu12','nvidia-cuda-cupti-cu12']:
 try:versions[package]=im.version(package)
 except im.PackageNotFoundError:versions[package]='NOT_DISTRIBUTION_METADATA'
versions['python']=sys.version
build=json.loads((REPO/'op-fused/config/same_q_v2_build_latest.json').read_text());assert build['binary_sha256']==sha(binary)
repos=[]
for p in [REPO/'op-fused/vendor/cutlass',REPO/'vendor/diff-gaussian-rasterization']:
 if (p/'.git').exists():repos.append(dict(path=str(p),commit=subprocess.check_output(['git','-C',str(p),'rev-parse','HEAD'],text=True).strip(),tracked_status=subprocess.check_output(['git','-C',str(p),'status','--porcelain','--untracked-files=no'],text=True)))
write(r/'compiled/EXTERNAL_DEPENDENCIES.json',dict(recorded_at=utc(),sources=rows,reused_binary=dict(path=str(binary),bytes=binary.stat().st_size,sha256=sha(binary),scope='Previously built Q1/CUTLASS ordinary scheduling control, not a V3 NUMA kernel; no V3 compile time attributed',original_build=build),versions=versions,vendor_repositories=repos,ldd=subprocess.check_output(['ldd',str(binary)],text=True),driver_backend='Source snapshot above; uses installed CUDA Driver API header. Actual API excerpts and header hash in local_api_evidence.json/CONTROL_LIMITATIONS.json.',vendor='Local Q1 vendor CUTLASS version.h reports3.5.1; do not confuse with the newer documentation version cited in task background. Full existing vendor trees/models remain at original local paths; compact archive is an analysis/review bundle, not a self-contained GPU distribution. Native renderer compiled-source snapshot and body audit retained.'))
print('external source snapshots',len(rows),'reused binary',sha(binary))
