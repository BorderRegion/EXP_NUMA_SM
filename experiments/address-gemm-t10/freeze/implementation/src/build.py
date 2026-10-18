from common import *
import sys,subprocess,time,shutil
sys.path.insert(0,'/home/ubuntu/projects/leetgpu-lab')
from lgjudge import cudabuild as cb
nv=Path('/home/ubuntu/projects/leetgpu-lab/.venv/lib/python3.12/site-packages/nvidia');out=ROOT/'build';t=time.monotonic()
base=[str(cb.find_nvcc()),'-std=c++17','-O3','-arch=sm_75','-ccbin',str(cb.find_host_compiler()),'-I'+str(REPO/'op-fused/vendor/cutlass/include'),'-I'+str(ROOT/'adapters'),'-I'+str(ROOT/'src'),*['-I'+str(x) for x in cb.include_dirs()]]
commands=[base+['--ptxas-options=-v','--cubin',str(ROOT/'src/address_kernels.cu'),'-o',str(out/'address.cubin')],base+['-DPC_DIAG=0','-Xcompiler=-fPIC','--shared','--cudart=none','-I'+str(nv/'cublas/include'),str(ROOT/'src/backend.cu'),'-Xlinker','/usr/lib/x86_64-linux-gnu/libcuda.so.1','-Xlinker',str(nv/'cublas/lib/libcublas.so.12'),'-Xlinker','-rpath','-Xlinker',str(nv/'cublas/lib'),'-o',str(out/'backend.so')]]
for i,cmd in enumerate(commands):
 p=subprocess.run(cmd,env=cb._subprocess_env(),text=True,capture_output=True);(out/f'compile{i}.log').write_text(p.stdout+p.stderr)
 if p.returncode:print(p.stdout,p.stderr);raise SystemExit(p.returncode)
p=subprocess.run(['/home/ubuntu/projects/leetgpu-lab/cuda/usr/bin/cuobjdump','--dump-sass',str(out/'address.cubin')],capture_output=True,text=True,check=True);(out/'address.sass').write_text(p.stdout)
write(out/'build.json',dict(commands=commands,build_seconds=time.monotonic()-t,sources={str(p.relative_to(ROOT)):sha(p) for d in ['src','adapters'] for p in (ROOT/d).glob('*') if p.is_file()},binaries={p.name:sha(p) for p in out.glob('*') if p.suffix in ['.cubin','.so']}))
print('BUILD_PASS',time.monotonic()-t)
