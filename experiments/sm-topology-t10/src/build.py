from pathlib import Path
import sys,subprocess,json,hashlib,time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,'/home/ubuntu/projects/leetgpu-lab')
from lgjudge import cudabuild as cb
b=ROOT/'build';b.mkdir(exist_ok=True)
cmds=[
 [str(cb.find_nvcc()),'-O3','-std=c++17','-arch=sm_75',f'-ccbin={cb.find_host_compiler()}',*[f'-I{x}' for x in cb.include_dirs()],'--ptxas-options=-v','--cubin',str(ROOT/'src/kernels.cu'),'-o',str(b/'probe.cubin')],
 ['g++','-O3','-std=c++17','-I/home/ubuntu/projects/leetgpu-lab/.venv/lib/python3.12/site-packages/nvidia/cuda_runtime/include','-I/home/ubuntu/projects/leetgpu-lab/cuda/usr/include',str(ROOT/'src/runner.cpp'),'/usr/lib/x86_64-linux-gnu/libcuda.so.1','-o',str(b/'runner')]]
for i,cmd in enumerate(cmds):
 p=subprocess.run(cmd,env=cb._subprocess_env(),capture_output=True,text=True);(b/f'compile_{i}.log').write_text(p.stdout+p.stderr);print(i,p.returncode,p.stderr[-4000:],flush=True)
 if p.returncode:raise SystemExit(p.returncode)
p=subprocess.run(['/home/ubuntu/projects/leetgpu-lab/cuda/usr/bin/cuobjdump','--dump-sass',str(b/'probe.cubin')],capture_output=True,text=True);(b/'probe.sass.txt').write_text(p.stdout+p.stderr)
(b/'build.json').write_text(json.dumps(dict(commands=cmds,source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'src').glob('*') if p.is_file()},binaries={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [b/'probe.cubin',b/'runner']}),indent=2))
