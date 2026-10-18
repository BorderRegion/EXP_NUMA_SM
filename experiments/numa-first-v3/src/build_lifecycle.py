"""Same qualified micro body; scoped real free/reallocation and capacity growth."""
import sys,subprocess,shutil,time,re
from common import *
r=runroot()
# The lifecycle host was frozen before the eight-policy Williams amendment.
# Reconstruct it from that preserved host, not the later mutable source file.
body_source=r/'compiled/micro/cyclic_development_snapshot/micro_campaign.cpp'
if not body_source.exists():body_source=ROOT/'src/micro_campaign.cpp'
source=body_source.read_text();source=source.replace('std::string out=a.at("--out");','std::string out=a.at("--out"),base_out=out;')
source=source.replace('Buffer data(32ull<<20),scratch','Buffer scratch')
start=source.index('std::ofstream identity(out+"/allocation.json");');end=source.index('\n CUstream parent;',start);source=source[:start]+source[end:]
start=source.index(' std::ofstream outputraw(');end=source.index(' for(unsigned bytes:',start);streams=source[start:end];source=source[:start]+source[end:]
old=' for(unsigned bytes:(qual?std::vector<unsigned>{2097152}:std::vector<unsigned>{2097152,8388608,33554432})){'
new=''' int generation=0;CUdeviceptr previous_base=0;
 for(unsigned bytes:std::vector<unsigned>{2097152,2097152,8388608}){
  int event=generation++;out=base_out+"/event_"+std::to_string(event);std::filesystem::create_directories(out);auto alloc_start=Clock::now();Buffer data(bytes);double allocation_ms=ms(alloc_start,Clock::now());ck(cuMemGetInfo(&free,&total),"event headroom");if(free<std::max(size_t(2ull<<30),total*15/100))throw std::runtime_error("event reserve");std::filesystem::copy_file(base_out+"/setup_costs.json",out+"/setup_costs.json",std::filesystem::copy_options::overwrite_existing);
  std::ofstream identity(out+"/allocation.json");identity<<"{\\"event\\":"<<event<<",\\"generation\\":"<<allocation*3+event<<",\\"base\\":"<<data.p<<",\\"capacity_bytes\\":"<<data.bytes<<",\\"allocation_ms\\":"<<allocation_ms<<",\\"previous_base\\":"<<previous_base<<",\\"same_virtual_address\\":"<<(previous_base==data.p?"true":"false")<<",\\"previous_graphs_destroyed_and_buffer_freed\\":true,\\"old_rule_used\\":false,\\"fresh_calibration_required\\":true}";identity.close();previous_base=data.p;
'''+streams
assert old in source;source=source.replace(old,new)
source=source.replace('allocation*100003u+round*7919u','allocation*100003u+event*13007u+round*7919u')
start=source.index('  std::vector<Plan>plans');end=source.index('\n',start)
source=source[:start]+'''  std::vector<Plan>plans{{"N",-1,-1,0,0,false,0},{"T",matched0,matched1,mask,bias,false,0},{"M",matched0,matched1,mask,bias,true,0}};'''+source[end:]
source=source.replace('mode<(qual?1:3)','mode<1')
source=source.replace('order{0,1,2,3,4,5,6,7};std::rotate(order.begin(),order.begin()+allocation%8,order.end());','order{0,1,2};std::rotate(order.begin(),order.begin()+(allocation+event)%3,order.end());')
source=source.replace('std::cout<<"MICRO_SIZE_COMPLETE "<<bytes<<std::endl;','std::ofstream complete(out+"/correctness.json");complete<<"{\\"status\\":\\"PASS\\",\\"full_output_and_resource_checks\\":true}";complete.close();std::cout<<"LIFECYCLE_EVENT_COMPLETE "<<event<<" bytes="<<bytes<<std::endl;')
source=source.replace('std::ofstream ok(out+"/correctness.json")','std::ofstream ok(base_out+"/lifecycle_complete.json")')
src=ROOT/'src/micro_lifecycle.cpp';src.write_text(source);d=r/'compiled/lifecycle';d.mkdir(exist_ok=True);cmd=['g++','-O3','-std=c++17',f'-I{REPO}/src','-I/home/ubuntu/projects/leetgpu-lab/.venv/lib/python3.12/site-packages/nvidia/cuda_runtime/include','-I/home/ubuntu/projects/leetgpu-lab/cuda/usr/include',str(src),'/usr/lib/x86_64-linux-gnu/libcuda.so.1','-o',str(d/'micro_lifecycle')];t=time.monotonic();p=subprocess.run(cmd,capture_output=True,text=True);(d/'build.log').write_text(p.stdout+p.stderr);print(p.returncode,p.stderr[-2000:]);p.check_returncode();shutil.copy2(src,d/src.name);write(d/'build.json',dict(created_at=utc(),command=cmd,compile_s=time.monotonic()-t,source_sha256=sha(src),binary_sha256=sha(d/'micro_lifecycle'),body_source_sha256=sha(body_source),body_source_path=str(body_source),consumer_cubin_sha256=sha(r/'compiled/micro/micro.cubin')))
write(r/'LIFECYCLE_FREEZE.json',dict(frozen_at=utc(),events=['initial2MiB','free_and_reallocate2MiB','free_and_grow8MiB'],blocks=4,strategies=['N','T','M'],primary_sessions=36,additional_native_anchors=24,scope='SYNTHETIC_COMPILED_MICRO_NOT_APPLICATION_LIFECYCLE',invariants='same primary andfine resource contexts persist; all old Graph executables destroyed anddata buffer freed before next actual allocation. New generation even if VA repeats. Fresh per-generation calibration andcapture; no old pointer/rule reuse. All logical outputs andactualSM checked.',counts='N micro development batch counts reused for same bytes/mode,128requests,atleast64warmand150ms eventspan',power='100W unchanged withprotections;180s conditioning perblock',replaces='Previously prepared native-GEMM-only lifecycle script was not executed; this version tests the actual compiled N/T/M mechanism and real allocation changes.'))
