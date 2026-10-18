from common import *
import sys,subprocess,time,difflib
sys.path.insert(0,'/home/ubuntu/projects/leetgpu-lab')
from lgjudge import cudabuild as cb
old=(ROOT/'support/vector_append.cu').read_text()
text=old.replace('__shared__ int page,source,last;','''__shared__ int page,source,last,job;
 // Each CTA claims one whole job. All per-page work is now read-only.
 if(threadIdx.x==0){
  const int*ls=p.list+head*(3+p.W*((p.NP+p.W/2-1)/(p.W/2)));
  if(p.mode==5){job=worker;source=worker>=ls[0];}
  else {int which=pref;unsigned i=atomicAdd(p.counter+head*3+which,1);
   if(i>=unsigned(ls[which])){which^=1;i=atomicAdd(p.counter+head*3+which,1);}
   job=i<unsigned(ls[which])?(which?ls[0]:0)+i:-1;source=which;
  }
 }
 __syncthreads();''')
a=text.index('   if(Queue){const int*ls=')
b=text.index('   if(Trace&&page>=0)',a)
text=text[:a]+'''   const int*ls=p.list+head*(3+p.W*((p.NP+p.W/2-1)/(p.W/2)));
   page=(job>=0&&iteration<ls[2])?ls[3+job*ls[2]+iteration]:-1;
'''+text[b:]
helper='''__device__ __forceinline__ uint4 load128(const uint4*p){uint4 v;
 asm volatile("ld.global.cg.v4.u32 {%0,%1,%2,%3}, [%4];":"=r"(v.x),"=r"(v.y),"=r"(v.z),"=r"(v.w):"l"(p):"memory");return v;}
'''
for variant in ['ca','cg']:
 s=text
 if variant=='cg':
  s=s.replace('struct Params',helper+'struct Params',1)
  for kv in ['k','v']:s=s.replace(f'((const uint4*)(p.{kv}+base))[i]',f'load128(((const uint4*)(p.{kv}+base))+i)')
 p=ROOT/f'src/claim_{variant}.cu';p.write_text(s)
 (ROOT/f'support/claim_{variant}.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile='frozen_vector_append.cu',tofile=p.name)))
 nv=Path('/home/ubuntu/projects/leetgpu-lab/.venv/lib/python3.12/site-packages/nvidia');t=time.monotonic()
 cmd=[str(cb.find_nvcc()),'-std=c++17','-O3','-arch=sm_75','-lineinfo','-ccbin',str(cb.find_host_compiler()),*['-I'+str(x) for x in cb.include_dirs()],'-Xcompiler=-fPIC','--shared','--cudart=none','--ptxas-options=-v',str(p),'-Xlinker','/usr/lib/x86_64-linux-gnu/libcuda.so.1','-Xlinker',str(nv/'cuda_runtime/lib/libcudart.so.12'),'-Xlinker','-rpath','-Xlinker',str(nv/'cuda_runtime/lib'),'-o',str(ROOT/f'build/claim_{variant}.so')]
 result=subprocess.run(cmd,env=cb._subprocess_env(),capture_output=True,text=True);(ROOT/f'build/claim_{variant}_compile.log').write_text(result.stdout+result.stderr)
 if result.returncode:print(result.stderr[-8000:]);raise SystemExit(result.returncode)
 ss=subprocess.run(['/home/ubuntu/projects/leetgpu-lab/cuda/usr/bin/cuobjdump','--dump-sass',str(ROOT/f'build/claim_{variant}.so')],capture_output=True,text=True,check=True);(ROOT/f'build/claim_{variant}.sass').write_text(ss.stdout)
 write(ROOT/f'build/claim_{variant}.json',dict(command=cmd,wall_seconds=time.monotonic()-t,source_sha256=sha(p),binary_sha256=sha(ROOT/f'build/claim_{variant}.so')))
 print('BUILD_PASS',variant,time.monotonic()-t,flush=True)
