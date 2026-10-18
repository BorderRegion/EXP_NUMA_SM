import sys,pathlib,subprocess,json,hashlib,datetime,time
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,'/home/ubuntu/projects/leetgpu-lab');from lgjudge import cudabuild as cb
start=time.perf_counter();out=ROOT/'build'/('sparse_'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'));out.mkdir(parents=True)
nvroot=pathlib.Path('/home/ubuntu/projects/leetgpu-lab/.venv/lib/python3.12/site-packages/nvidia')
commands=[[str(cb.find_nvcc()),'-O3','-std=c++17','-arch=sm_75',f'-ccbin={cb.find_host_compiler()}','--ptxas-options=-v',*[f'-I{x}' for x in cb.include_dirs()],'--cubin',str(ROOT/'src/sparse_kernels.cu'),'-o',str(out/'sparse.cubin')],['g++','-O3','-std=c++17',f'-I{nvroot}/cuda_runtime/include',f'-I{nvroot}/cusparse/include',f'-I{nvroot}/cuda_cccl/include','-I/home/ubuntu/projects/leetgpu-lab/cuda/usr/include',str(ROOT/'src/sparse_runner.cpp'),'/usr/lib/x86_64-linux-gnu/libcuda.so.1',f'{nvroot}/cusparse/lib/libcusparse.so.12',f'-Wl,--disable-new-dtags,-rpath,{nvroot}/cusparse/lib:{nvroot}/nvjitlink/lib:{nvroot}/cuda_runtime/lib','-o',str(out/'sparse_runner')]]
for i,cmd in enumerate(commands):
 p=subprocess.run(cmd,env=cb._subprocess_env(),capture_output=True,text=True);(out/f'compile_{i}.txt').write_text(p.stdout+p.stderr);print(p.stderr[-2000:]);
 if p.returncode:raise SystemExit('build failed '+str(out))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
(out/'build.json').write_text(json.dumps(dict(build_id=out.name,recipes=commands,source_hashes={p.name:sha(p) for p in [ROOT/'src/sparse_runner.cpp',ROOT/'src/sparse_kernels.cu',ROOT/'src/driver_backend.hpp']},binary_hashes={p.name:sha(p) for p in [out/'sparse.cubin',out/'sparse_runner']},compilation_ms=1000*(time.perf_counter()-start),cusparse_reference_commit='07c4f09223302ce4310eef945ed458e092598d17'),indent=2))
p=ROOT/'build/sparse_current';p.unlink(missing_ok=True);p.symlink_to(out.name);print(out)
