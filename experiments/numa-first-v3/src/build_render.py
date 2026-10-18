import concurrent.futures,os,shutil,subprocess,sys,time
from common import *
sys.path.insert(0,'/home/ubuntu/projects/leetgpu-lab');from lgjudge import cudabuild as cb
r=runroot();out=r/'compiled/render';out.mkdir(exist_ok=True);src=out/'source';src.mkdir(exist_ok=True)
for p in (REPO/'build/renderer_source').iterdir():
 if p.is_file():shutil.copy2(p,src/p.name)
s=(src/'forward.cu').read_text();start=s.index('template <uint32_t CHANNELS>\n__global__ void __launch_bounds__(BLOCK_X * BLOCK_Y)\nrenderMappedCUDA(');end=s.index('\nvoid FORWARD::render(',start);s=s[:start]+s[end:]
s=s[:s.index('\nvoid ec_launch_mapped(')]
s=s.replace(' if(ec_active){ec_dispatch(ec_last_args);return;}','')
s+='''
void v3_native_snapshot(const RenderArgs&a,cudaStream_t stream){
 renderCUDA<NUM_CHANNELS><<<dim3((a.width+15)/16,(a.height+15)/16),dim3(BLOCK_X,BLOCK_Y),0,stream>>>(a.ranges,a.point_list,a.width,a.height,a.means2D,a.colors,a.conic,a.final_T,a.n_contrib,a.background,a.out_color);
}
'''
(src/'forward.cu').write_text(s)
for p in [ROOT/'src/render_native.cpp',REPO/'src/driver_backend.hpp',REPO/'src/render_dispatch.h']:shutil.copy2(p,src/p.name)
nv=Path('/home/ubuntu/projects/leetgpu-lab/.venv/lib/python3.12/site-packages/nvidia')
inc=[REPO/'vendor/cub',REPO/'vendor/thrust',src,REPO/'vendor/diff-gaussian-rasterization/third_party/glm',nv/'cuda_cupti/include',*cb.include_dirs()]
base=[str(cb.find_nvcc()),'-O3','-std=c++17','-arch=sm_75',f'-ccbin={cb.find_host_compiler()}','--ptxas-options=-v',*[f'-I{x}' for x in inc],*[f'-L{x}' for x in cb.library_dirs()]]
commands=[base+['-c',str(src/name),'-o',str(out/(Path(name).stem+'.o'))] for name in ['forward.cu','backward.cu','rasterizer_impl.cu']]
commands.append(['g++','-O3','-std=c++17',f'-I{src}',f'-I{nv}/cuda_runtime/include',f'-I{nv}/cuda_cupti/include','-I/home/ubuntu/projects/leetgpu-lab/cuda/usr/include','-c',str(src/'render_native.cpp'),'-o',str(out/'render_native.o')])
def compile(item):
 i,cmd=item;p=subprocess.run(cmd,env=cb._subprocess_env(),text=True,capture_output=True);(out/f'compile_{i}.log').write_text(p.stdout+p.stderr);print(i,p.returncode,p.stderr[-1500:],flush=True);return p.returncode
start=time.monotonic()
if '--link-only' in sys.argv:codes=[]
else:
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:codes=list(pool.map(compile,enumerate(commands)))
if any(codes):raise SystemExit('compile failure')
link=base+[*map(str,out.glob('*.o')),'-Xlinker','/usr/lib/x86_64-linux-gnu/libcuda.so.1','-Xlinker',str(nv/'cuda_cupti/lib/libcupti.so.12'),'-Xlinker','-rpath','-Xlinker',str(nv/'cuda_cupti/lib'),'-o',str(out/'render_native')]
if compile((len(commands),link)):raise SystemExit('link failure')
write(out/'build.json',dict(created_at=utc(),commands=commands+[link],compile_s=time.monotonic()-start,binary_sha256=sha(out/'render_native'),sources={p.name:sha(p) for p in src.iterdir() if p.is_file()},native_render_body='unchanged upstream renderCUDA; mapped kernel removed; only snapshot entry added'))
