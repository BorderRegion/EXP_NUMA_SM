#!/usr/bin/env python3
"""Reuse the local, rootless toolkit. Record the exact recipe once per build."""
import sys,os,pathlib,subprocess,json,hashlib,time,datetime
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,'/home/ubuntu/projects/leetgpu-lab')
from lgjudge import cudabuild as cb
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def main():
 start=time.perf_counter();stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ');out=ROOT/'build'/stamp;out.mkdir(parents=True)
 base=[str(cb.find_nvcc()),'-O3','-std=c++17','-arch=sm_75',f'-ccbin={cb.find_host_compiler()}','--ptxas-options=-v']+[f'-I{x}' for x in cb.include_dirs()]+[f'-L{x}' for x in cb.library_dirs()]
 jobs=[(base+['--cubin',str(ROOT/'src/micro_kernels.cu'),'-o',str(out/'micro.cubin')],cb._subprocess_env()),(base+[str(ROOT/'GPU_COMPUTE_TOPOLOGY_DUAL_20261014/starter_cuda/device_probe.cu'),'-o',str(out/'device_probe')],cb._subprocess_env())]
 if (ROOT/'src/micro_runner.cpp').exists():jobs.append((['g++','-O3','-std=c++17','-I/home/ubuntu/projects/leetgpu-lab/.venv/lib/python3.12/site-packages/nvidia/cuda_runtime/include',str(ROOT/'src/micro_runner.cpp'),'/usr/lib/x86_64-linux-gnu/libcuda.so.1','-o',str(out/'micro_runner')],dict(os.environ)))
 recipes=[]
 for i,(cmd,env) in enumerate(jobs):
  p=subprocess.run(cmd,env=env,text=True,capture_output=True);(out/f'compile_{i}.txt').write_text(p.stdout+p.stderr);recipes.append(dict(command=cmd,returncode=p.returncode));print(p.stderr[-3000:]);
  if p.returncode: raise SystemExit(f'compile failed; logs {out}')
 record=dict(build_id=stamp,recipes=recipes,source_hashes={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'src').glob('*')},binary_hashes={p.name:sha(p) for p in out.iterdir() if p.suffix not in ['.txt','.json']},compilation_ms=1000*(time.perf_counter()-start),nvcc=cb.nvcc_version(cb.find_nvcc()),host_compiler=subprocess.run([str(cb.find_host_compiler()),'--version'],capture_output=True,text=True).stdout,git_commit=subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,text=True,capture_output=True).stdout.strip() or None,git_dirty=bool(subprocess.run(['git','status','--porcelain'],cwd=ROOT,text=True,capture_output=True).stdout))
 (out/'build.json').write_text(json.dumps(record,indent=2));link=ROOT/'build/current';link.unlink(missing_ok=True);link.symlink_to(out.name);print(out)
if __name__=='__main__':main()
