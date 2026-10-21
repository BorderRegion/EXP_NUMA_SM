from common import *
import sys,subprocess,time
sys.path.insert(0,'/home/ubuntu/projects/leetgpu-lab')
from lgjudge import cudabuild as cb
nv=Path('/home/ubuntu/projects/leetgpu-lab/.venv/lib/python3.12/site-packages/nvidia')
build=ROOT/'build';build.mkdir(exist_ok=True)
name=sys.argv[1] if len(sys.argv)>1 else 'bridge'
src=ROOT/'src'/f'{name}.cu';out=build/f'{name}.so';t=time.monotonic()
cmd=[str(cb.find_nvcc()),'-std=c++17','-O3','-arch=sm_75','-lineinfo','-ccbin',str(cb.find_host_compiler()),*['-I'+str(x) for x in cb.include_dirs()],'-Xcompiler=-fPIC','--shared','--cudart=none','--ptxas-options=-v',str(src),'-Xlinker','/usr/lib/x86_64-linux-gnu/libcuda.so.1','-Xlinker',str(nv/'cuda_runtime/lib/libcudart.so.12'),'-Xlinker','-rpath','-Xlinker',str(nv/'cuda_runtime/lib'),'-o',str(out)]
p=subprocess.run(cmd,env=cb._subprocess_env(),capture_output=True,text=True);(build/f'{name}_compile.log').write_text(p.stdout+p.stderr)
if p.returncode:print(p.stderr[-6000:]);raise SystemExit(p.returncode)
q=subprocess.run(['/home/ubuntu/projects/leetgpu-lab/cuda/usr/bin/cuobjdump','--dump-sass',str(out)],capture_output=True,text=True,check=True);(build/f'{name}.sass').write_text(q.stdout)
write(build/f'{name}_build.json',dict(command=cmd,wall_seconds=time.monotonic()-t,source_sha256=sha(src),binary_sha256=sha(out)));print('BUILD_PASS',name,round(time.monotonic()-t,3))
