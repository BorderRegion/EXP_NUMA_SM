from pathlib import Path
import sys,subprocess,time,json,hashlib,shutil
root=Path(__file__).resolve().parents[1];sys.path.insert(0,'/home/ubuntu/projects/leetgpu-lab')
from lgjudge import cudabuild as cb
nv=Path('/home/ubuntu/projects/leetgpu-lab/.venv/lib/python3.12/site-packages/nvidia')
stamp=time.strftime('%Y%m%dT%H%M%SZ',time.gmtime());out=root/'build'/stamp;out.mkdir()
commands=[];logs=[];t=time.monotonic()
base=[str(cb.find_nvcc()),'-std=c++17','-O3','-arch=sm_75','-ccbin',str(cb.find_host_compiler()),'-I'+str(root.parent/'op-fused/vendor/cutlass/include'),'-I'+str(root/'adapters'),'-I'+str(root/'src'),*['-I'+str(x) for x in cb.include_dirs()]]
for diag in [0,1]:
 if len(sys.argv)>1:
  shutil.copy2(Path(sys.argv[1])/f'diag{diag}.cubin',out/f'diag{diag}.cubin');shutil.copy2(Path(sys.argv[1])/f'diag{diag}.sass',out/f'diag{diag}.sass');continue
 cmd=base+[f'-DPC_DIAG={diag}','--ptxas-options=-v','--cubin',str(root/'src/kernels.cu'),'-o',str(out/f'diag{diag}.cubin')];commands.append(cmd)
 p=subprocess.run(cmd,env=cb._subprocess_env(),text=True,capture_output=True);(out/f'diag{diag}.log').write_text(p.stdout+p.stderr)
 if p.returncode:print(p.stderr[-10000:]);raise SystemExit(p.returncode)
 sass=subprocess.check_output(['/home/ubuntu/projects/leetgpu-lab/cuda/usr/bin/cuobjdump','--dump-sass',str(out/f'diag{diag}.cubin')],text=True);(out/f'diag{diag}.sass').write_text(sass)
 if not diag:assert 'SR_SMID' not in sass and 'SR_CLOCK' not in sass and 'HMMA' in sass
cmd=base+['-DPC_DIAG=0','-Xcompiler=-fPIC','--shared','--cudart=none','-I'+str(nv/'cublas/include'),'-I'+str(root.parent/'src'),'-I'+str(root.parent/'numa-first-v3/src'),str(root/'src/backend.cu'),'-Xlinker','/usr/lib/x86_64-linux-gnu/libcuda.so.1','-Xlinker',str(nv/'cublas/lib/libcublas.so.12'),'-Xlinker','-rpath','-Xlinker',str(nv/'cublas/lib'),'-o',str(out/'backend.so')];commands.append(cmd)
p=subprocess.run(cmd,env=cb._subprocess_env(),text=True,capture_output=True);(out/'host.log').write_text(p.stdout+p.stderr)
record={'commands':commands,'cpu_build_s':time.monotonic()-t,'returncode':p.returncode,'sources':{str(x.relative_to(root)):hashlib.sha256(x.read_bytes()).hexdigest() for d in ['src','adapters'] for x in (root/d).glob('*') if x.is_file()}}
for rel,digest in record['sources'].items():
 f=root/rel
 if f.suffix in ['.cu','.cuh','.hpp','.h'] or f.name=='build.py':
  target=out/'source'/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,target)
shutil.copy2(root.parent/'src/driver_backend.hpp',out/'source/driver_backend.hpp')
(out/'build.json').write_text(json.dumps(record,indent=2));print(out,p.returncode,flush=True)
if p.returncode:print(p.stderr[-10000:]);raise SystemExit(p.returncode)
(root/'BUILD.txt').write_text(str(out)+'\n')
