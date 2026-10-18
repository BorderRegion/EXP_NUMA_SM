from common import *
import sys,subprocess,os
sys.path.insert(0,'/home/ubuntu/projects/leetgpu-lab')
from lgjudge import cudabuild as cb
nv=Path('/home/ubuntu/projects/leetgpu-lab/.venv/lib/python3.12/site-packages/nvidia')
commands={}
for name in ['tail_probe','diagnostic']:
    cmd=[str(cb.find_nvcc()),'-O3','-std=c++17','-arch=sm_75','-lineinfo','-ccbin',str(cb.find_host_compiler()),*['-I'+str(x) for x in cb.include_dirs()],'-Xcompiler=-fPIC','--shared','--cudart=none','--ptxas-options=-v',str(ROOT/'src'/f'{name}.cu'),'-Xlinker',str(nv/'cuda_runtime/lib/libcudart.so.12'),'-Xlinker','-rpath','-Xlinker',str(nv/'cuda_runtime/lib'),'-o',str(ROOT/'build'/f'{name}.so')]
    p=subprocess.run(cmd,env=cb._subprocess_env(),capture_output=True,text=True);(ROOT/'build'/f'{name}_compile.log').write_text(p.stdout+p.stderr);assert p.returncode==0,p.stderr;commands[name]=cmd
cmd=['g++','-O3','-std=c++17','-fPIC','-shared','-I'+str(nv/'cuda_runtime/include'),str(ROOT/'src/shared_graph.cpp'),'-lcuda','-o',str(ROOT/'build/shared_graph.so')]
p=subprocess.run(cmd,capture_output=True,text=True);(ROOT/'build/shared_compile.log').write_text(p.stdout+p.stderr);assert p.returncode==0,p.stderr;commands['shared_graph']=cmd
write(ROOT/'build/BUILD.json',dict(commands=commands,binaries={p.name:sha(p) for p in (ROOT/'build').glob('*.so')}));print('BUILD PASS',flush=True)
