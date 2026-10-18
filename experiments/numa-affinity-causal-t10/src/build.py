from common import *
import sys,subprocess,time
sys.path.insert(0,'/home/ubuntu/projects/leetgpu-lab')
from lgjudge import cudabuild as cb
nv=Path('/home/ubuntu/projects/leetgpu-lab/.venv/lib/python3.12/site-packages/nvidia');start=time.monotonic()
cmd=[str(cb.find_nvcc()),'-O3','-std=c++17','-arch=sm_75','-lineinfo','-ccbin',str(cb.find_host_compiler()),*['-I'+str(x) for x in cb.include_dirs()],'-Xcompiler=-fPIC','--shared','--cudart=none','--ptxas-options=-v',str(ROOT/'src/causal.cu'),'-Xlinker',str(nv/'cuda_runtime/lib/libcudart.so.12'),'-Xlinker','-rpath','-Xlinker',str(nv/'cuda_runtime/lib'),'-o',str(ROOT/'build/causal.so')]
p=subprocess.run(cmd,env=cb._subprocess_env(),capture_output=True,text=True);(ROOT/'build/causal_compile.log').write_text(p.stdout+p.stderr);assert p.returncode==0,p.stderr
p=subprocess.run(['/home/ubuntu/projects/leetgpu-lab/cuda/usr/bin/cuobjdump','--dump-sass',str(ROOT/'build/causal.so')],capture_output=True,text=True,check=True);(ROOT/'build/causal.sass').write_text(p.stdout)
write(ROOT/'build/causal_build.json',dict(command=cmd,wall_seconds=time.monotonic()-start,hashes={str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'src/causal.cu',ROOT/'build/causal.so']}));print('CONST_BUILD_PASS')
