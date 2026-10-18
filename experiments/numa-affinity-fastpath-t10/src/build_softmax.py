from common import *
import sys,subprocess
sys.path.insert(0,'/home/ubuntu/projects/leetgpu-lab')
from lgjudge import cudabuild as cb
nv=Path('/home/ubuntu/projects/leetgpu-lab/.venv/lib/python3.12/site-packages/nvidia')
base=[str(cb.find_nvcc()),'-std=c++17','-O3','-arch=sm_75','-lineinfo','-ccbin',str(cb.find_host_compiler()),*['-I'+str(x) for x in cb.include_dirs()],'--ptxas-options=-v']
commands=[base+['--cubin',str(ROOT/'src/probe8.cu'),'-o',str(ROOT/'build/probe8.cubin')],['g++','-O3','-std=c++17','-I'+str(nv/'cuda_runtime/include'),'-I/home/ubuntu/projects/leetgpu-lab/cuda/usr/include',str(ROOT/'src/probe8_runner.cpp'),'/usr/lib/x86_64-linux-gnu/libcuda.so.1','-o',str(ROOT/'build/probe8_runner')],base+['-Xcompiler=-fPIC','--shared','--cudart=none',str(ROOT/'src/softmax.cu'),'-Xlinker','/usr/lib/x86_64-linux-gnu/libcuda.so.1','-Xlinker',str(nv/'cuda_runtime/lib/libcudart.so.12'),'-Xlinker','-rpath','-Xlinker',str(nv/'cuda_runtime/lib'),'-o',str(ROOT/'build/softmax.so')]]
for i,cmd in enumerate(commands):
 p=subprocess.run(cmd,env=cb._subprocess_env(),capture_output=True,text=True);(ROOT/f'build/soft_compile_{i}.log').write_text(p.stdout+p.stderr);print(i,p.returncode,flush=True)
 if p.returncode:print(p.stderr[-6000:]);raise SystemExit(p.returncode)
for f in ['softmax.so','probe8.cubin']:
 p=subprocess.run(['/home/ubuntu/projects/leetgpu-lab/cuda/usr/bin/cuobjdump','--dump-sass',str(ROOT/'build'/f)],capture_output=True,text=True,check=True);(ROOT/'build'/(f+'.sass')).write_text(p.stdout)
write(ROOT/'build/softmax_build.json',dict(commands=commands,hashes={str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'src/softmax.cu',ROOT/'src/probe8.cu',ROOT/'src/probe8_runner.cpp',ROOT/'build/softmax.so',ROOT/'build/probe8.cubin',ROOT/'build/probe8_runner']}))
