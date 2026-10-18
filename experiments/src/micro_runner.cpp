#include "driver_backend.hpp"
#include <cstdint>
#include <fstream>
#include <iostream>
#include <iomanip>
#include <algorithm>
#include <numeric>
#include <map>
#include <set>
#include <filesystem>
#include <memory>
struct Task{int family,units;};
static uint32_t step(uint32_t x,uint32_t j,uint32_t id){return x*1664525u+1013904223u+(j^id);}
static unsigned long long digest_cpu(const std::vector<uint32_t>&x){unsigned long long v=0;for(size_t i=0;i<x.size();i++)v+=(unsigned long long)x[i]*(i+1);return v;}
int main(int argc,char**argv){try{
 std::map<std::string,std::string> a;for(int i=1;i+1<argc;i+=2)a[argv[i]]=argv[i+1];
 auto get=[&](std::string k,std::string def){return a.count(k)?a[k]:def;};
 int fam=std::stoi(get("--family","0")),size=std::stoi(get("--size","0")),layout=std::stoi(get("--layout","1"));std::string mode=get("--mode","native"),out=get("--out",".");
 int nt=std::stoi(get("--tasks",size==0?"256":size==1?"1024":"4096"));int stride=(fam==3||fam<0)?(size==0?2048:size==1?4096:8192):128;
 int cache_n=std::min(nt*1024,1<<(18+size));int threads=128;
 if(size<0||size>2||nt<1||nt>8192)throw std::runtime_error("bounds");
 int warm=std::stoi(get("--warmup","32")),epochs=std::stoi(get("--epochs","128"));bool diag_only=get("--diagnostic","0")=="1";
 if(epochs<1||epochs>512||warm<0||warm>4096)throw std::runtime_error("epoch bound");
 std::filesystem::create_directories(out);auto init_start=Clock::now();Backend b(mode=="native"?-1:mode=="full"?0:layout);int ng=b.groups.size();
 std::vector<Task> meta(nt);for(int t=0;t<nt;t++){int f=fam<0?t%3==0?0:t%3==1?2:3:fam;int units=f==0?(size==0?64:size==1?256:512):f==1?(size==0?8:size==1?32:64):f==2?(size==0?16:size==1?64:128):1;meta[t]={f,units};}
 if(a.count("--task-file")){std::ifstream f(a["--task-file"]);for(auto&t:meta)if(!(f>>t.family>>t.units))throw std::runtime_error("task file too short");}
 std::vector<int> ownership(nt),table;std::vector<std::vector<int>> lists(ng);
 if(a.count("--plan")){std::ifstream f(a["--plan"]);for(int&t:ownership)if(!(f>>t)||t<0||t>=ng)throw std::runtime_error("invalid plan");}
 else for(int t=0;t<nt;t++){int cumulative=0;for(int g=0;g<ng;g++){cumulative+=b.groups[g].sms;if((long long)t*b.sms<(long long)cumulative*nt){ownership[t]=g;break;}}}
 for(int t=0;t<nt;t++)lists[ownership[t]].push_back(t);
 std::vector<int> offsets(ng);for(int g=0;g<ng;g++){offsets[g]=table.size();table.insert(table.end(),lists[g].begin(),lists[g].end());}
 {std::ofstream f(out+"/task_map.csv");f<<"task,family,units,group\n";for(int t=0;t<nt;t++)f<<t<<','<<meta[t].family<<','<<meta[t].units<<','<<ownership[t]<<'\n';}
 size_t nin=std::max((size_t)nt*stride,(size_t)cache_n),nout=(size_t)nt*stride;
 if((nin+nout)*4+nt*40>512ull*1024*1024)throw std::runtime_error("micro memory budget exceeded");
 std::vector<uint32_t> input(nin),expected(nout,0),output(nout),diag(nt*4);for(size_t i=0;i<nin;i++)input[i]=uint32_t(i)*747796405u+uint32_t(2026101404);
 // Full CPU reference, every output element; unsigned modulo 2^32.
 for(int t=0;t<nt;t++){Task m=meta[t];for(int lane=0;lane<128;lane++){uint32_t id=t*128+lane,v=0;
  if(m.family==0){uint32_t x=input[id%cache_n],y=x^0x9e3779b9u,z=x+0x1234567u,w=x^id;for(int j=0;j<m.units;j++){x=step(x,j,id);y=step(y,j,id+1);z=step(z,j,id+2);w=step(w,j,id+3);}v=x^y^z^w;}
  else if(m.family==1){for(int j=0;j<m.units;j++)v+=input[(t*128+(lane+j)%128+j*128)%cache_n]*3u+uint32_t(j);}
  else if(m.family==2){for(int j=0;j<m.units;j++)v=step(v,input[(t*1024+lane+(j%8)*128)%cache_n],j);}
  else{for(int j=lane;j<stride;j+=128){size_t off=(size_t)t*stride+j;expected[off]=input[off]*3u+uint32_t(off);}continue;}
  expected[(size_t)t*stride+lane]=v;
 }}
 Buffer din(nin*4),dout(nout*4),dmeta(nt*sizeof(Task)),dtable(nt*4),ddiag(nt*16),ddigest(8);
 din.upload(input.data());dmeta.upload(meta.data());dtable.upload(table.data());ck(cuMemsetD32(dout.p,0,nout),"output reset");ck(cuMemsetD32(ddiag.p,0,nt*4),"diag reset");ck(cuCtxSynchronize(),"init ready");
 std::vector<CUmodule> modules(ng);std::vector<CUfunction> kernels(ng),digests(ng);std::vector<int> occupancy(ng),grids(ng);unsigned shared=0;for(auto&m:meta)if(m.family==1)shared=std::max(shared,unsigned(m.units*128*4));
 int regs=0;for(int g=0;g<ng;g++){b.current(g);ck(cuModuleLoad(&modules[g],get("--cubin","build/current/micro.cubin").c_str()),"load cubin");ck(cuModuleGetFunction(&kernels[g],modules[g],"micro"),"micro function");ck(cuModuleGetFunction(&digests[g],modules[g],"digest"),"digest function");ck(cuOccupancyMaxActiveBlocksPerMultiprocessor(&occupancy[g],kernels[g],threads,shared),"occupancy");ck(cuFuncGetAttribute(&regs,CU_FUNC_ATTRIBUTE_NUM_REGS,kernels[g]),"regs");grids[g]=mode=="native"?nt:std::min((int)lists[g].size(),b.groups[g].sms*occupancy[g]*std::stoi(get("--grid-multiple","1")));}
 ck(cuCtxSetCurrent(b.primary),"primary");auto init_end=Clock::now();
 auto launch=[&](int g,int diagnose){auto&grp=b.groups[g];b.current(g);int count=lists[g].size(),native_mode=mode=="native"?1:0;CUdeviceptr map=mode=="native"?0:dtable.p+offsets[g]*4;void*args[]={&din.p,&dout.p,&dmeta.p,&map,&count,&stride,&cache_n,&native_mode,&diagnose,&ddiag.p};ck(cuEventRecord(grp.start,grp.stream),"event start");if(count)ck(cuLaunchKernel(kernels[g],grids[g],1,1,threads,1,1,shared,grp.stream,args,nullptr),"micro launch");ck(cuEventRecord(grp.end,grp.stream),"event end");};
 auto run=[&](int diagnose){auto start=Clock::now();for(int g=0;g<ng;g++){launch(g,diagnose);if(mode=="isolated")ck(cuStreamSynchronize(b.groups[g].stream),"isolated join");}b.join();return ms(start,Clock::now());};
 // Exactly-once and complete numerical qualification through the deployed map.
 run(1);dout.download(output.data());ddiag.download(diag.data());
 for(int t=0;t<nt;t++)if(diag[t*4]!=1)throw std::runtime_error("exactly-once failure at "+std::to_string(t));
 for(size_t i=0;i<nout;i++)if(output[i]!=expected[i])throw std::runtime_error("CPU bitwise mismatch at "+std::to_string(i));
 {std::ofstream f(out+"/topology.csv");f<<"task,group,sm_begin,sm_end,worker,executions\n";for(int t=0;t<nt;t++)f<<t<<','<<ownership[t]<<','<<diag[t*4+1]<<','<<diag[t*4+2]<<','<<diag[t*4+3]<<','<<diag[t*4]<<'\n';}
 unsigned long long expect_digest=digest_cpu(expected),got=0;
 auto screen=[&](){b.current(0);void*args[]={&dout.p,&ddigest.p,&nout};ck(cuLaunchKernel(digests[0],1,1,1,256,1,1,0,b.groups[0].stream,args,nullptr),"digest launch");ck(cuStreamSynchronize(b.groups[0].stream),"digest join");ddigest.download(&got);if(got!=expect_digest)throw std::runtime_error("digest mismatch");};
 std::ofstream frames(out+"/frames.csv"),groups(out+"/groups.csv");frames<<"epoch,cpu_ready_ms,gpu_event_max_ms,digest,planner_calls,plan_D2H_bytes,plan_H2D_bytes,recompile_count\n";groups<<"epoch,group,tasks,sms,gpu_event_ms,tasks_per_ms\n";frames<<std::setprecision(10);groups<<std::setprecision(10);
 double total_cpu=0,max_kernel=0,screen_ms=0;auto worker_start=Clock::now();
 for(int e=-warm;e<epochs;e++){double cpu=run(diag_only?1:0);std::vector<float> times(ng);for(int g=0;g<ng;g++){b.current(g);ck(cuEventElapsedTime(&times[g],b.groups[g].start,b.groups[g].end),"elapsed");if(times[g]>20)throw std::runtime_error("micro kernel interval exceeds 20ms; reduce mechanical size");max_kernel=std::max(max_kernel,double(times[g]));}auto s=Clock::now();screen();screen_ms+=ms(s,Clock::now());
  if(e>=0){total_cpu+=cpu;frames<<e<<','<<cpu<<','<<*std::max_element(times.begin(),times.end())<<','<<got<<",0,0,0,0\n";for(int g=0;g<ng;g++)groups<<e<<','<<g<<','<<lists[g].size()<<','<<b.groups[g].sms<<','<<times[g]<<','<<(times[g]>0?lists[g].size()/times[g]:0)<<'\n';}
 }
 double worker_ms=ms(worker_start,Clock::now());ck(cuCtxSetCurrent(b.primary),"final primary");dout.download(output.data());for(size_t i=0;i<nout;i++)if(output[i]!=expected[i])throw std::runtime_error("final full mismatch at "+std::to_string(i));
 {std::ofstream f(out+"/correctness.json");f<<"{\"status\":\"PASS\",\"cpu_reference_full\":true,\"exactly_once\":true,\"final_full_bitwise\":true,\"output_elements\":"<<nout<<",\"digest\":"<<expect_digest<<"}\n";}
 {std::ofstream f(out+"/summary.json");f<<std::setprecision(12)<<"{\"status\":\"SUCCESS\",\"family\":"<<fam<<",\"size\":"<<size<<",\"tasks\":"<<nt<<",\"stride\":"<<stride<<",\"cache_elements\":"<<cache_n<<",\"mode\":\""<<mode<<"\",\"layout\":"<<layout<<",\"groups\":[";for(int g=0;g<ng;g++){if(g)f<<',';f<<"{\"sms\":"<<b.groups[g].sms<<",\"tasks\":"<<lists[g].size()<<",\"occupancy_blocks_per_sm\":"<<occupancy[g]<<",\"grid\":"<<grids[g]<<"}";}f<<"],\"registers\":"<<regs<<",\"dynamic_shared_bytes\":"<<shared<<",\"device_memory_bytes\":"<<(din.bytes+dout.bytes+dmeta.bytes+dtable.bytes+ddiag.bytes+ddigest.bytes)<<",\"init_ms\":"<<ms(init_start,init_end)<<",\"worker_seconds\":"<<worker_ms/1000<<",\"mean_cpu_ready_ms\":"<<total_cpu/epochs<<",\"max_kernel_interval_ms\":"<<max_kernel<<",\"observation_ms\":"<<screen_ms<<",\"epochs\":"<<epochs<<",\"warmups\":"<<warm<<"}\n";}
 for(int g=0;g<ng;g++){b.current(g);ck(cuModuleUnload(modules[g]),"unload");}ck(cuCtxSetCurrent(b.primary),"cleanup primary");
 std::cout<<"SUCCESS "<<out<<" cpu_ms="<<total_cpu/epochs<<'\n';return 0;
}catch(std::exception&e){std::cerr<<e.what()<<'\n';return 2;}}
