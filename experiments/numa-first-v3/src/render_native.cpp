#include "driver_backend.hpp"
#include "render_dispatch.h"
#include "rasterizer.h"
#include <cuda_runtime_api.h>
#include <cupti.h>
#include <fstream>
#include <iostream>
#include <iomanip>
#include <filesystem>
#include <vector>
#include <map>
#include <set>
#include <algorithm>
#include <cstring>
#include <cmath>
#include <array>
bool ec_active=false;RenderArgs ec_last_args{};static CUevent upstream_end;
void ec_before_render(){ck(cuEventRecord(upstream_end,nullptr),"upstream event");}
void ec_dispatch(const RenderArgs&){throw std::runtime_error("Legacy scheduler forbidden in native-only runner");}
void v3_native_snapshot(const RenderArgs&,cudaStream_t stream);
static void rt(cudaError_t e,const char*w){if(e)throw std::runtime_error(std::string(w)+": "+cudaGetErrorString(e));}
struct Grow {CUdeviceptr p=0;size_t bytes=0;unsigned growths=0;char*get(size_t n){if(n>bytes){size_t target=(n+1048575)/1048576*1048576,free,total;ck(cuMemGetInfo(&free,&total),"growth headroom");if(free+bytes<target+std::max(size_t(2ull<<30),total*15/100))throw std::runtime_error("Renderer growth would breach VRAM reserve");if(p)cuMemFree(p);p=0;bytes=target;ck(cuMemAlloc(&p,bytes),"grow");growths++;}return (char*)p;}~Grow(){if(p)cuMemFree(p);}};
struct Camera {unsigned id;float tanx,tany,view[16],proj[16],pos[3];};
static void read(std::ifstream&f,void*p,size_t n){if(!f.read((char*)p,n))throw std::runtime_error("truncated input");}
struct Output{std::vector<float>color,T;std::vector<unsigned>contrib;};
static Output output(int w,int h){Output o;o.color.resize(size_t(w)*h*3);o.T.resize(size_t(w)*h);o.contrib.resize(size_t(w)*h);ck(cuMemcpyDtoH(o.color.data(),(CUdeviceptr)ec_last_args.out_color,o.color.size()*4),"color");ck(cuMemcpyDtoH(o.T.data(),(CUdeviceptr)ec_last_args.final_T,o.T.size()*4),"T");ck(cuMemcpyDtoH(o.contrib.data(),(CUdeviceptr)ec_last_args.n_contrib,o.contrib.size()*4),"contrib");for(float x:o.color)if(!std::isfinite(x))throw std::runtime_error("nonfinite color");return o;}
static bool equal(const Output&a,const Output&b){return !memcmp(a.color.data(),b.color.data(),a.color.size()*4)&&!memcmp(a.T.data(),b.T.data(),a.T.size()*4)&&!memcmp(a.contrib.data(),b.contrib.data(),a.contrib.size()*4);}
static uint64_t hash(const Output&o){uint64_t h=1469598103934665603ull;auto part=[&](const void*p,size_t n){auto q=(const unsigned char*)p;for(size_t i=0;i<n;i++)h=(h^q[i])*1099511628211ull;};part(o.color.data(),o.color.size()*4);part(o.T.data(),o.T.size()*4);part(o.contrib.data(),o.contrib.size()*4);return h;}
static void representative(const std::string&path,const Output&o){if(std::filesystem::exists(path))return;std::ofstream f(path,std::ios::binary);f.write((char*)o.color.data(),o.color.size()*4);f.write((char*)o.T.data(),o.T.size()*4);f.write((char*)o.contrib.data(),o.contrib.size()*4);if(!f)throw std::runtime_error("representative output write");}
static bool tracing=false;static std::ofstream trace;
static void CUPTIAPI callback(void*,CUpti_CallbackDomain domain,CUpti_CallbackId id,const void*raw){if(!tracing)return;if(domain!=CUPTI_CB_DOMAIN_RUNTIME_API&&domain!=CUPTI_CB_DOMAIN_DRIVER_API)return;auto*d=(const CUpti_CallbackData*)raw;if(d->callbackSite!=CUPTI_API_ENTER)return;const char*name=d->functionName?d->functionName:"";bool kernel_launch=strstr(name,"LaunchKernel")||strstr(name,"LaunchCooperativeKernel");const char*symbol=kernel_launch?d->symbolName:nullptr;trace<<domain<<','<<id<<','<<d->correlationId<<','<<std::quoted(name)<<','<<std::quoted(symbol?symbol:"")<<'\n';}
int main(int argc,char**argv){try{
 std::map<std::string,std::string>a;for(int i=1;i+1<argc;i+=2)a[argv[i]]=argv[i+1];auto get=[&](std::string k,std::string d){return a.count(k)?a[k]:d;};
 std::string assets=get("--assets",""),out=get("--out",".");int w=std::stoi(get("--width","1920")),h=std::stoi(get("--height","1080")),seq=std::stoi(get("--sequence","0")),frames=std::stoi(get("--frames","256")),warm_min=std::stoi(get("--warmup","128"));bool profile=get("--profile","0")=="1";
 std::filesystem::create_directories(out);auto init=Clock::now();Backend b(-1);ck(cuEventCreate(&upstream_end,0),"upstream");CUevent begin,end;ck(cuEventCreate(&begin,0),"begin");ck(cuEventCreate(&end,0),"end");
 unsigned n;std::ifstream mf(assets+"/model.bin",std::ios::binary);read(mf,&n,4);std::vector<float>model(size_t(n)*59);read(mf,model.data(),model.size()*4);Buffer dmodel(model.size()*4);dmodel.upload(model.data());float*ptr=(float*)dmodel.p;float*xyz=ptr;ptr+=n*3;float*opacity=ptr;ptr+=n;float*scale=ptr;ptr+=n*3;float*rotation=ptr;ptr+=n*4;float*sh=ptr;
 unsigned nc;std::ifstream cf(assets+"/cameras_"+std::to_string(w)+"x"+std::to_string(h)+".bin",std::ios::binary);read(cf,&nc,4);std::vector<Camera>cams(nc);read(cf,cams.data(),cams.size()*sizeof(Camera));std::vector<int>selected;for(unsigned i=0;i<nc;i++)if(int(i%4)==2+seq)selected.push_back(i);if(selected.empty())throw std::runtime_error("empty camera set");
 Buffer dcam(35*4),dout(size_t(w)*h*3*4),dbg(12),scratch(128ull<<20),scratchout(256*8);float bg[3]={0,0,0};dbg.upload(bg);Grow geometry,binning,img;ck(cuMemsetD32(scratch.p,0x12345678,scratch.bytes/4),"scratch init");
 CUmodule module;ck(cuModuleLoad(&module,get("--cubin","").c_str()),"sweep module");CUfunction sweep;ck(cuModuleGetFunction(&sweep,module,"sweep"),"sweep function");
 auto evict=[&](){unsigned words=scratch.bytes/4;void*args[]={&scratch.p,&words,&scratchout.p};ck(cuLaunchKernel(sweep,256,1,1,128,1,1,0,nullptr,args,nullptr),"eviction");ck(cuCtxSynchronize(),"eviction ready");};
 auto render=[&](int ci){Camera&c=cams.at(ci);float cam[35];memcpy(cam,c.view,64);memcpy(cam+16,c.proj,64);memcpy(cam+32,c.pos,12);auto t=Clock::now();dcam.upload(cam);ck(cuEventRecord(begin,nullptr),"begin frame");
  int instances=CudaRasterizer::Rasterizer::forward([&](size_t x){return geometry.get(x);},[&](size_t x){return binning.get(x);},[&](size_t x){return img.get(x);},n,3,16,(float*)dbg.p,w,h,xyz,sh,nullptr,opacity,scale,1.f,rotation,nullptr,(float*)dcam.p,(float*)dcam.p+16,(float*)dcam.p+32,c.tanx,c.tany,false,(float*)dout.p,nullptr,false);
  rt(cudaGetLastError(),"render");ck(cuEventRecord(end,nullptr),"end frame");ck(cuEventSynchronize(end),"frame ready");float all,up;ck(cuEventElapsedTime(&all,begin,end),"frame event");ck(cuEventElapsedTime(&up,begin,upstream_end),"up event");double ready_ms=ms(t,Clock::now());size_t free,total;ck(cuMemGetInfo(&free,&total),"frame memory reserve");if(free<std::max(size_t(2ull<<30),total*15/100))throw std::runtime_error("VRAM reserve");return std::array<double,4>{ready_ms,all,up,double(instances)};
 };
 CUgraphExec snapshot_graph=nullptr;
 auto snapshot=[&](){auto t=Clock::now();ck(cuEventRecord(begin,nullptr),"snapshot begin");if(snapshot_graph)ck(cuGraphLaunch(snapshot_graph,nullptr),"snapshot graph");else v3_native_snapshot(ec_last_args,nullptr);rt(cudaGetLastError(),"snapshot launch");ck(cuEventRecord(end,nullptr),"snapshot end");ck(cuEventSynchronize(end),"snapshot ready");float dev;ck(cuEventElapsedTime(&dev,begin,end),"snapshot event");return std::array<double,4>{ms(t,Clock::now()),dev,0,0};};
 render(selected[0]);size_t free,total;ck(cuMemGetInfo(&free,&total),"headroom");if(free<std::max(size_t(2ull<<30),total*15/100))throw std::runtime_error("headroom");double init_ms=ms(init,Clock::now());
 trace.open(out+"/native_api_trace.csv");trace<<"domain,cbid,correlation,function,symbol\n";CUpti_SubscriberHandle subscriber;CUptiResult tr=CUPTI_ERROR_NOT_INITIALIZED;
 if(profile){tr=cuptiSubscribe(&subscriber,callback,nullptr);if(tr==CUPTI_SUCCESS){cuptiEnableDomain(1,subscriber,CUPTI_CB_DOMAIN_RUNTIME_API);cuptiEnableDomain(1,subscriber,CUPTI_CB_DOMAIN_DRIVER_API);tracing=true;render(selected[0]);tracing=false;cuptiUnsubscribe(subscriber);}}
 std::ofstream mix(out+"/tile_access.csv");mix<<"tile,list_length,unique_gaussians,unique_virtual4k_color_pages,majority_virtual_page_fraction,actual_home_known_fraction\n";
 if(profile){int nt=((w+15)/16)*((h+15)/16);std::vector<uint2>ranges(nt);ck(cuMemcpyDtoH(ranges.data(),(CUdeviceptr)ec_last_args.ranges,nt*sizeof(uint2)),"ranges");unsigned count=0;for(auto r:ranges)count=std::max(count,r.y);std::vector<unsigned>ids(count);ck(cuMemcpyDtoH(ids.data(),(CUdeviceptr)ec_last_args.point_list,count*4),"point list");
  for(int t=0;t<nt;t++){std::set<unsigned>unique;std::map<uint64_t,unsigned>pages;for(unsigned j=ranges[t].x;j<ranges[t].y;j++){unsigned id=ids[j];unique.insert(id);pages[(uint64_t(ec_last_args.colors)+uint64_t(id)*12)/4096]++;}unsigned largest=0;for(auto&p:pages)largest=std::max(largest,p.second);unsigned len=ranges[t].y-ranges[t].x;mix<<t<<','<<len<<','<<unique.size()<<','<<pages.size()<<','<<(len?double(largest)/len:0)<<",0\n";}
  std::ofstream ptrs(out+"/address_scope.json");ptrs<<"{\"colors_base\":"<<uint64_t(ec_last_args.colors)<<",\"means2D_base\":"<<uint64_t(ec_last_args.means2D)<<",\"conic_base\":"<<uint64_t(ec_last_args.conic)<<",\"point_list_entries\":"<<count<<",\"attribute_bytes_upper_bound\":"<<uint64_t(n)*(12+8+16)<<",\"virtual_pages_not_homes\":true}\n";
 }
 std::ofstream samples(out+"/samples.csv"),checks(out+"/checks.csv");samples<<std::setprecision(12);samples<<"scope,request,camera_id,cpu_ready_ms,event_ms,upstream_ms,instances,cache_prepare_ms,monotonic_start_ns\n";checks<<"scope,request,camera_id,raw_bit_equal,hash\n";
 std::ofstream graphlog(out+"/graph_nodes.csv");graphlog<<"scope,nodes,kernel_nodes\n";
 auto phase=[&](std::string scope){bool dynamic=scope=="DYNAMIC_PRODUCED",evicted=scope=="SNAPSHOT_EVICTED";render(selected[0]);auto ref=output(w,h);
  if(!dynamic){CUgraph graph;ck(cuStreamBeginCapture(b.groups[0].stream,CU_STREAM_CAPTURE_MODE_GLOBAL),"capture begin");v3_native_snapshot(ec_last_args,(cudaStream_t)b.groups[0].stream);rt(cudaGetLastError(),"capture launch");ck(cuStreamEndCapture(b.groups[0].stream,&graph),"capture end");size_t nodes=0;ck(cuGraphGetNodes(graph,nullptr,&nodes),"graph nodes");if(nodes!=1)throw std::runtime_error("native snapshot graph is not one kernel");ck(cuGraphInstantiate(&snapshot_graph,graph,0),"graph instantiate");graphlog<<scope<<','<<nodes<<",1\n";cuGraphDestroy(graph);}
  auto warm_start=Clock::now();int warm=0;
  do{if(dynamic)render(selected[warm%selected.size()]);else{if(evicted)evict();snapshot();}warm++;}while(warm<warm_min||ms(warm_start,Clock::now())<2000);
  if(!dynamic){render(selected[0]);ref=output(w,h);}
  for(int j=0;j<frames;j++){auto start_ns=std::chrono::duration_cast<std::chrono::nanoseconds>(Clock::now().time_since_epoch()).count();int ci=dynamic?selected[j%selected.size()]:selected[0];double prep_ms=0;if(evicted){auto t=Clock::now();evict();prep_ms=ms(t,Clock::now());}auto timing=dynamic?render(ci):snapshot();samples<<scope<<','<<j<<','<<cams[ci].id<<','<<timing[0]<<','<<timing[1]<<','<<timing[2]<<','<<timing[3]<<','<<prep_ms<<','<<start_ns<<'\n';
   if(j==0||j==frames/2||j==frames-1){auto got=output(w,h);if(dynamic){render(ci);ref=output(w,h);}if(!equal(got,ref))throw std::runtime_error("raw-bit render mismatch");auto digest=hash(got);checks<<scope<<','<<j<<','<<cams[ci].id<<",1,"<<digest<<'\n';if(profile)representative(out+"/representative_"+std::to_string(digest)+".bin",got);}
  }samples.flush();checks.flush();if(snapshot_graph){cuGraphExecDestroy(snapshot_graph);snapshot_graph=nullptr;}std::cout<<"PHASE_COMPLETE "<<scope<<" warm="<<warm<<" measured="<<frames<<std::endl;
 };
 std::vector<std::string>scopes{"DYNAMIC_PRODUCED","SNAPSHOT_HOT","SNAPSHOT_EVICTED"};int block=std::stoi(get("--block","0"));std::rotate(scopes.begin(),scopes.begin()+block%3,scopes.end());for(auto scope:scopes)phase(scope);
 std::ofstream summary(out+"/summary.json");summary<<"{\"status\":\"PASS\",\"gaussians\":"<<n<<",\"width\":"<<w<<",\"height\":"<<h<<",\"sequence\":"<<seq<<",\"frames_per_scope\":"<<frames<<",\"initialization_ms\":"<<init_ms<<",\"model_bytes\":"<<dmodel.bytes<<",\"geometry_bytes\":"<<geometry.bytes<<",\"binning_bytes\":"<<binning.bytes<<",\"image_bytes\":"<<img.bytes<<",\"scratch_bytes\":"<<scratch.bytes<<",\"free_bytes\":"<<free<<",\"cupti_subscribe_status\":"<<tr<<",\"native_original_pixel_order\":true,\"candidate_present\":false,\"graph\":\"dynamic pipeline not captured due host-visible rendered-count dependency; both snapshot states use one-kernel CUDA Graph\"}\n";
 cuModuleUnload(module);cuEventDestroy(begin);cuEventDestroy(end);cuEventDestroy(upstream_end);return 0;
}catch(std::exception&e){std::cerr<<e.what()<<'\n';return 2;}}
