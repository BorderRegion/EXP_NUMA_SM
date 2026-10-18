from common import *
import ctypes as C
C.CDLL('/home/ubuntu/projects/leetgpu-lab/.venv/lib/python3.12/site-packages/nvidia/cuda_runtime/lib/libcudart.so.12',mode=C.RTLD_GLOBAL)
build=Path((ROOT/'BUILD.txt').read_text().strip());host=C.CDLL(str(build/'backend.so'));cpu=C.CDLL(str(ROOT/'build/policy_cpu_frozen.so'));cpu.v2_choose_cpu.argtypes=[C.c_int]*6+[C.POINTER(C.c_double)];host.sr_choose.argtypes=host.sr_choose_dynamic.argtypes=[C.c_int]*5+[C.POINTER(C.c_double)]
rows=[]
for c in read(INPUT/'plans/cases.json'):
 for p in range(5):
  for h in [0,1,32,256,1024,4096]:
   for dyn in [0,1]:
    a=(C.c_double*13)();b=(C.c_double*13)();cpu.v2_choose_cpu(c['M'],c['N'],c['K'],p,h,dyn,a);rc=(host.sr_choose_dynamic if dyn else host.sr_choose)(c['M'],c['N'],c['K'],p,h,b);assert rc==0
    err=max(abs(x-y)/max(1,abs(x)) for x,y in zip(a,b));assert err<1e-12 and list(a)[:3]==list(b)[:3];rows.append(dict(case=c['id'],policy=p,H=h,dynamic=dyn,relative_error=err))
write(ROOT/'reports/DEPLOYED_HOST_CPU_EQUIVALENCE.json',dict(status='PASS',n=len(rows),max_relative_error=max(x['relative_error'] for x in rows),rows=rows,scope='Only pure C++ choose entry points called. No Engine, CUDA context creation, Graph or GPU work.'))
write(ROOT/'freeze/EXECUTION_FREEZE.json',dict(created_at=utc(),build=str(build),binaries={p.name:sha(p) for p in build.iterdir() if p.suffix in ['.cubin','.so']},model_sha=sha(ROOT/'freeze/POLICY_FREEZE.json'),choice_sha=sha(ROOT/'freeze/choices_before_timing.json'),sources={p.name:sha(p) for p in (ROOT/'src').glob('*') if p.suffix in ['.hpp','.cu','.cuh']},status='FROZEN_BEFORE_CONFIRMATION'))
print('DEPLOYED_HOST_EQUIVALENCE_PASS',len(rows))
