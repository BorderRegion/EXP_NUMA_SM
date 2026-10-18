from common import *
import subprocess
nv=Path('/home/ubuntu/projects/leetgpu-lab/.venv/lib/python3.12/site-packages/nvidia')
cmd=['g++','-O3','-std=c++17','-fPIC','-shared','-I'+str(nv/'cuda_runtime/include'),str(ROOT/'src/shared_graph.cpp'),'-lcuda','-o',str(ROOT/'build/shared_graph.so')]
p=subprocess.run(cmd,capture_output=True,text=True);(ROOT/'build/shared_compile.log').write_text(p.stdout+p.stderr)
assert p.returncode==0,p.stderr
write(ROOT/'build/BUILD.json',dict(command=cmd,binary_sha256=sha(ROOT/'build/shared_graph.so')))
print('HOST SAMPLER BUILD PASS; no new GPU kernel')
