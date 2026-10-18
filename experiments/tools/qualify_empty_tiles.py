"""Additional correctness-only empty/nonempty transition fixture; no timed cohort changes."""
from runlib import *
import sys,shutil,hashlib,os,fcntl
sys.path.insert(0,'/home/ubuntu/projects/leetgpu-lab');from lgjudge import cudabuild as cb
base=(ROOT/'build/renderer_current').resolve();out=ROOT/'build/renderer_empty_fixture';out.mkdir(exist_ok=True)
source=(ROOT/'src/renderer_runner.cpp').read_text();source=source.replace('bool ec_active=false;','static bool empty_fixture=false;\nbool ec_active=false;')
source=source.replace('Camera&c=cams.at(ci);','Camera c=cams.at(ci);if(empty_fixture){float delta=-1000000.f-c.view[14];c.view[14]+=delta;c.proj[14]+=delta*(100.f/(100.f-.01f));c.proj[15]+=delta;}')
source=source.replace('for(int j=0;j<length;j++){int ci=', 'for(int j=0;j<length;j++){empty_fixture=(j%4==0);int ci=')
source=source.replace('auto reference=read_output(w,h);for(int repeat=', 'auto reference=read_output(w,h);if(empty_fixture){for(float v:reference.T)if(v!=1.f)throw std::runtime_error("empty final_T");for(unsigned v:reference.contrib)if(v)throw std::runtime_error("empty contributors");}for(int repeat=')
src=out/'renderer_empty.cpp';src.write_text(source);header='/home/ubuntu/projects/leetgpu-lab/.venv/lib/python3.12/site-packages/nvidia/cuda_runtime/include'
commands=[['g++','-O3','-std=c++17','-I'+header,'-I/home/ubuntu/projects/leetgpu-lab/cuda/usr/include','-I'+str(ROOT/'src'),'-I'+str(ROOT/'build/renderer_source'),'-c',str(src),'-o',str(out/'renderer_empty.o')]]
commands.append([str(cb.find_nvcc()),f'-ccbin={cb.find_host_compiler()}',*[f'-I{x}'for x in cb.include_dirs()],*[f'-L{x}'for x in cb.library_dirs()],*[str(p)for p in base.glob('*.o')if p.name!='renderer_runner.o'],str(out/'renderer_empty.o'),'-Xlinker','/usr/lib/x86_64-linux-gnu/libcuda.so.1','-o',str(out/'renderer_runner')])
with open(ROOT/'environment/gpu_worker.lock','w')as lock:
 fcntl.flock(lock,fcntl.LOCK_EX)
 for i,cmd in enumerate(commands):
  p=subprocess.run(cmd,env=cb._subprocess_env(),capture_output=True,text=True);(out/f'compile_{i}.txt').write_text(p.stdout+p.stderr)
  if p.returncode:raise RuntimeError(p.stderr)
(out/'build.json').write_text(json.dumps(dict(purpose='correctness fixture only',parent_build=base.name,recipes=commands,source_sha256=sha(src),binary_sha256=sha(out/'renderer_runner')),indent=2))
decision('D013','Original selected scene frames contain no empty tiles. Add a correctness-only coherent camera-translation fixture producing fully empty views, alternating empty/nonempty views across 16 frames, 321x181 and 720p, preserving original body and finalT=1/ncontrib=0 contract. Timed build remains unchanged; fixture build is separate and never pooled into timings.')
for w,h in [(321,181),(1280,720)]:
 p,m=run('W1_empty_qualification',dict(width=w,height=h,frames=16,purpose='empty/nonempty reset transition fixture'),['--assets',str(ROOT/'assets/prepared/bonsai'),'--purpose','qualify','--policies','NI','--frames',16,'--width',w,'--height',h],executable='renderer_runner',build=out)
 if m['status']!='SUCCESS':raise RuntimeError(p)
