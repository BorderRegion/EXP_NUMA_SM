from runlib import *
import sys,shutil
sys.path.insert(0,'/home/ubuntu/projects/leetgpu-lab');from lgjudge import cudabuild as cb
out=ROOT/'build'/('supplement_address_'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'));out.mkdir();src=ROOT/'src/supplement';nvroot=pathlib.Path('/home/ubuntu/projects/leetgpu-lab/.venv/lib/python3.12/site-packages/nvidia');commands=[]
commands.append([str(cb.find_nvcc()),'-O3','-std=c++17','-arch=sm_75',f'-ccbin={cb.find_host_compiler()}',*[f'-I{x}' for x in cb.include_dirs()],'--ptxas-options=-v','--cubin',str(src/'address_kernels.cu'),'-o',str(out/'address.cubin')])
for name in ['address_probe_runner','address_deploy_runner']:commands.append(['g++','-O3','-std=c++17',f'-I{ROOT}/src',f'-I{nvroot}/cuda_runtime/include','-I/home/ubuntu/projects/leetgpu-lab/cuda/usr/include',str(src/(name+'.cpp')),'/usr/lib/x86_64-linux-gnu/libcuda.so.1','-o',str(out/name)])
for i,cmd in enumerate(commands):
 p=subprocess.run(cmd,env=cb._subprocess_env(),capture_output=True,text=True);(out/f'compile_{i}.log').write_text(p.stdout+p.stderr);print(i,p.returncode,p.stderr[-2000:],flush=True)
 if p.returncode:raise SystemExit('Failed build preserved '+str(out))
ss=out/'source_snapshot';ss.mkdir()
for f in [*src.glob('address*'),ROOT/'src/driver_backend.hpp']:shutil.copy2(f,ss/f.name)
(out/'build.json').write_text(json.dumps(dict(created_at=utc(),build_id=out.name,commands=commands,sources={str(f.relative_to(ROOT)):sha(f) for f in ss.iterdir()},binaries={n:sha(out/n) for n in ['address.cubin','address_probe_runner','address_deploy_runner']}),indent=2))
link=ROOT/'build/supplement_address_current';link.unlink(missing_ok=True);link.symlink_to(out.name);print(out)
