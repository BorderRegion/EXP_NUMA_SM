import os,shutil,subprocess,sys,time
from common import *
sys.path.insert(0,'/home/ubuntu/projects/leetgpu-lab');from lgjudge import cudabuild as cb
out=runroot()/'compiled';src=ROOT/'src';start=time.monotonic()
nvroot=Path('/home/ubuntu/projects/leetgpu-lab/.venv/lib/python3.12/site-packages/nvidia')
commands=[
 [str(cb.find_nvcc()),'-O3','-std=c++17','-arch=sm_75',f'-ccbin={cb.find_host_compiler()}',*[f'-I{x}' for x in cb.include_dirs()],'--ptxas-options=-v','--cubin',str(src/'probe.cu'),'-o',str(out/'probe.cubin')],
 ['g++','-O3','-std=c++17',f'-I{REPO}/src',f'-I{nvroot}/cuda_runtime/include','-I/home/ubuntu/projects/leetgpu-lab/cuda/usr/include',str(src/'probe_runner.cpp'),'/usr/lib/x86_64-linux-gnu/libcuda.so.1','-o',str(out/'probe_runner')]]
for i,cmd in enumerate(commands):
 p=subprocess.run(cmd,env=cb._subprocess_env(),capture_output=True,text=True);(out/f'probe_compile_{i}.log').write_text(p.stdout+p.stderr)
 print(i,p.returncode,p.stderr[-2000:],flush=True)
 if p.returncode:raise SystemExit('Compile failed; logs retained')
ss=out/'probe_source';ss.mkdir(exist_ok=True)
for p in [src/'probe.cu',src/'probe_types.hpp',src/'probe_runner.cpp',REPO/'src/driver_backend.hpp',src/'build_probe.py']:shutil.copy2(p,ss/p.name)
write(out/'probe_build.json',dict(created_at=utc(),commands=commands,compile_s=time.monotonic()-start,sources={p.name:sha(p) for p in ss.iterdir()},binaries={p.name:sha(p) for p in [out/'probe.cubin',out/'probe_runner']}))
cuobj='/home/ubuntu/projects/leetgpu-lab/cuda/usr/bin/cuobjdump'
p=subprocess.run([cuobj,'--dump-sass',str(out/'probe.cubin')],capture_output=True,text=True);(out/'probe.sass.txt').write_text(p.stdout+p.stderr)
