from common import *
import sys,subprocess,time
sys.path.insert(0,'/home/ubuntu/projects/leetgpu-lab')
from lgjudge import cudabuild as cb
nv=Path('/home/ubuntu/projects/leetgpu-lab/.venv/lib/python3.12/site-packages/nvidia');start=time.monotonic()
cmd=[str(cb.find_nvcc()),'-O3','-std=c++17','-arch=sm_75','-lineinfo','-ccbin',str(cb.find_host_compiler()),*['-I'+str(x) for x in cb.include_dirs()],'-Xcompiler=-fPIC','--shared','--cudart=none','--ptxas-options=-v',str(ROOT/'src/softmax_const.cu'),'-Xlinker',str(nv/'cuda_runtime/lib/libcudart.so.12'),'-Xlinker','-rpath','-Xlinker',str(nv/'cuda_runtime/lib'),'-o',str(ROOT/'build/softmax_const.so')]
p=subprocess.run(cmd,env=cb._subprocess_env(),capture_output=True,text=True);(ROOT/'build/const_compile.log').write_text(p.stdout+p.stderr);assert p.returncode==0,p.stderr
p=subprocess.run(['/home/ubuntu/projects/leetgpu-lab/cuda/usr/bin/cuobjdump','--dump-sass',str(ROOT/'build/softmax_const.so')],capture_output=True,text=True,check=True);(ROOT/'build/softmax_const.sass').write_text(p.stdout)
write(ROOT/'build/const_build.json',dict(command=cmd,wall_seconds=time.monotonic()-start,hashes={str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'src/softmax_const.cu',ROOT/'build/softmax_const.so']}));print('CONST_BUILD_PASS')
