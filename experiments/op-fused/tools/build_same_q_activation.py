"""CPU-only compilation using existing rootless toolkit; no GPU runtime invoked."""
import datetime,hashlib,json,pathlib,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,'/home/ubuntu/projects/leetgpu-lab')
from lgjudge import cudabuild as cb
start=time.monotonic()
stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
out=ROOT/'build'/('same_q_activation_'+stamp);out.mkdir(parents=True)
cuda_runtime=pathlib.Path('/home/ubuntu/projects/leetgpu-lab/.venv/lib/python3.12/site-packages/nvidia/cuda_runtime/lib/libcudart.so.12')
command=[str(cb.find_nvcc()),'-std=c++17','-O3','-arch=sm_75','-ccbin',str(cb.find_host_compiler()),
  '-Xcompiler=-fPIC','--shared','--cudart=none','--ptxas-options=-v',
  '-I'+str(ROOT/'vendor/cutlass/include'),'-I'+str(ROOT/'src'),
  *['-I'+str(p) for p in cb.include_dirs()],str(ROOT/'src/same_q_v2/activation.cu'),
  '-Xlinker',str(cuda_runtime),'-Xlinker','-rpath','-Xlinker',str(cuda_runtime.parent),
  '-o',str(out/'libopf_activation.so')]
result=subprocess.run(command,env=cb._subprocess_env(),text=True,capture_output=True)
(out/'build_stdout.txt').write_text(result.stdout);(out/'build_stderr.txt').write_text(result.stderr)
record=dict(command=command,returncode=result.returncode,cpu_build_wall_seconds=time.monotonic()-start,
  gpu_worker_seconds=0,build_helper_sha256=hashlib.sha256(pathlib.Path(cb.__file__).read_bytes()).hexdigest(),
  sources={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'src/same_q_v2').glob('*') if p.is_file()})
if result.returncode==0:
 binary=(out/'libopf_activation.so').read_bytes();(ROOT/'src/same_q_v2/libopf_activation.so').write_bytes(binary)
 record['binary_sha256']=hashlib.sha256(binary).hexdigest();record['binary_bytes']=len(binary)
(out/'build.json').write_text(json.dumps(record,indent=2)+'\n')
(ROOT/'config/same_q_v2_activation_build_latest.json').write_text(json.dumps(dict(build_dir=str(out),**record),indent=2)+'\n')
print(json.dumps(dict(build_dir=str(out),returncode=result.returncode,seconds=record['cpu_build_wall_seconds']),indent=2),flush=True)
if result.returncode:print(result.stderr[-7000:])
sys.exit(result.returncode)
