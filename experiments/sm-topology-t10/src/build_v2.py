from common import *
import sys,subprocess,shutil
sys.path.insert(0,'/home/ubuntu/projects/leetgpu-lab')
from lgjudge import cudabuild as cb
b=ROOT/'build_v2';b.mkdir(exist_ok=True)
s=(ROOT/'src/kernels.cu').read_text();s=s.replace('if(p.kind==3)base=flags+blockIdx.x*1024;','if(p.kind==3)base=flags+offsets[p.slot%3]/4+blockIdx.x*1024;').replace('base=flags+map[sm*2]*1024;','base=flags+offsets[p.slot%3]/4+map[sm*2]*1024;')
(b/'kernels_v2.cu').write_text(s);shutil.copy2(ROOT/'src/types.hpp',b/'types.hpp');shutil.copy2(ROOT/'build/runner',b/'runner')
cmd=[str(cb.find_nvcc()),'-O3','-std=c++17','-arch=sm_75',f'-ccbin={cb.find_host_compiler()}',*[f'-I{x}' for x in cb.include_dirs()],'--ptxas-options=-v','--cubin',str(b/'kernels_v2.cu'),'-o',str(b/'probe.cubin')]
p=subprocess.run(cmd,env=cb._subprocess_env(),capture_output=True,text=True);(b/'compile.log').write_text(p.stdout+p.stderr);print(p.returncode,p.stderr)
if p.returncode:raise SystemExit(p.returncode)
p=subprocess.run(['/home/ubuntu/projects/leetgpu-lab/cuda/usr/bin/cuobjdump','--dump-sass',str(b/'probe.cubin')],capture_output=True,text=True);(b/'probe.sass.txt').write_text(p.stdout+p.stderr)
write(b/'build.json',dict(command=cmd,change='Only kind3 flag base offsets for address-shift control; old build untouched',files={p.name:sha(p) for p in b.iterdir() if p.is_file()}))
