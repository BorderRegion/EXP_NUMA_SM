import sys,subprocess,shutil,time,re,json
from frozen_common import *
sys.path.insert(0,'/home/ubuntu/projects/leetgpu-lab');from lgjudge import cudabuild as cb
r=runroot();d=r/'compiled';commands=[];start=time.monotonic();audit={}
for diag in [0,1]:
 out=d/f'consumer_diag{diag}.cubin';cmd=[str(cb.find_nvcc()),'-O3','-std=c++17','-arch=sm_75',f'-ccbin={cb.find_host_compiler()}',*[f'-I{x}' for x in cb.include_dirs()],f'-DFROZEN_DIAG={diag}','--ptxas-options=-v','--cubin',str(ROOT/'src/frozen_consume.cu'),'-o',str(out)];commands.append(cmd)
 p=subprocess.run(cmd,env=cb._subprocess_env(),capture_output=True,text=True);(d/f'diag{diag}_build.log').write_text(p.stdout+p.stderr);p.check_returncode()
 sass=subprocess.check_output(['/home/ubuntu/projects/leetgpu-lab/cuda/usr/bin/cuobjdump','--dump-sass',str(out)],text=True);(d/f'diag{diag}.sass.txt').write_text(sass)
 specials=[x.strip() for x in sass.splitlines() if any(k in x for k in ['SR_SMID','SR_CLOCK','ATOM','RED.'])]
 audit[str(diag)]=dict(special_instructions=specials,output_store_lines=[x.strip() for x in sass.splitlines() if 'STG.' in x],kernel_names=re.findall(r'Function : (\w+)',sass),sha256=sha(out))
 if not diag:assert not specials and len(audit[str(diag)]['output_store_lines'])==3,'Only one required sum store per clean kernel, no diagnostic stores'
cmd=['g++','-O3','-std=c++17',f'-I{REPO}/src','-I/home/ubuntu/projects/leetgpu-lab/.venv/lib/python3.12/site-packages/nvidia/cuda_runtime/include','-I/home/ubuntu/projects/leetgpu-lab/cuda/usr/include',str(ROOT/'src/frozen_campaign.cpp'),'/usr/lib/x86_64-linux-gnu/libcuda.so.1','-o',str(d/'frozen_campaign')];commands.append(cmd)
p=subprocess.run(cmd,capture_output=True,text=True);(d/'host_build.log').write_text(p.stdout+p.stderr);print(p.stderr[-4000:]);p.check_returncode()
for name in ['frozen_consume.cu','frozen_consumer.cuh','frozen_campaign.cpp','frozen_resources.hpp','probe_types.hpp']:shutil.copy2(ROOT/'src'/name,d/name)
shutil.copy2(REPO/'src/driver_backend.hpp',d/'driver_backend.hpp')
write(d/'build.json',dict(built_at=utc(),compile_s=time.monotonic()-start,commands=commands,sources={p.name:sha(p) for p in d.iterdir() if p.suffix in ['.cu','.cpp','.hpp','.cuh']},binaries={p.name:sha(p) for p in d.iterdir() if p.suffix=='.cubin' or p.name=='frozen_campaign'},sass_audit=audit,scope='Compile-time DIAG0 removes all SM/clock/ownership/diagnostic writes and atomics; required exact sum output store remains. Static instruction counts are not dynamic costs.'))
print('build and clean SASS audit PASS')
