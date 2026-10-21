from common import *
import sys,subprocess,time
sys.path.insert(0,'/home/ubuntu/projects/leetgpu-lab')
from lgjudge import cudabuild as cb
nv=Path('/home/ubuntu/projects/leetgpu-lab/.venv/lib/python3.12/site-packages/nvidia');t=time.monotonic()
cmd=[str(cb.find_nvcc()),'-std=c++17','-O3','-arch=sm_75','-lineinfo','-ccbin',str(cb.find_host_compiler()),*['-I'+str(x) for x in cb.include_dirs()],'-Xcompiler=-fPIC','--shared','--cudart=none','--ptxas-options=-v',str(ROOT/'src/vector_append.cu'),'-Xlinker','/usr/lib/x86_64-linux-gnu/libcuda.so.1','-Xlinker',str(nv/'cuda_runtime/lib/libcudart.so.12'),'-Xlinker','-rpath','-Xlinker',str(nv/'cuda_runtime/lib'),'-o',str(ROOT/'build/vector_append.so')]
p=subprocess.run(cmd,env=cb._subprocess_env(),capture_output=True,text=True);(ROOT/'build/vector_append_compile.log').write_text(p.stdout+p.stderr)
if p.returncode:print(p.stderr[-8000:]);raise SystemExit(p.returncode)
p=subprocess.run(['/home/ubuntu/projects/leetgpu-lab/cuda/usr/bin/cuobjdump','--dump-sass',str(ROOT/'build/vector_append.so')],capture_output=True,text=True,check=True);(ROOT/'build/vector_append.sass').write_text(p.stdout)
write(ROOT/'build/vector_append_build.json',dict(command=cmd,wall_seconds=time.monotonic()-t,source_sha256=sha(ROOT/'src/vector_append.cu'),binary_sha256=sha(ROOT/'build/vector_append.so')));print('BUILD_PASS',time.monotonic()-t)
