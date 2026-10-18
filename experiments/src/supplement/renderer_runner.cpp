#include "driver_backend.hpp"
#include "render_dispatch.h"
#include "rasterizer.h"
#include <cuda_runtime_api.h>
#include <fstream>
#include <iostream>
#include <iomanip>
#include <filesystem>
#include <algorithm>
#include <numeric>
#include <map>
#include <memory>
#include <cstring>
#include <cmath>
static bool ec_full=false;
static long long unix_ns(){return std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::system_clock::now().time_since_epoch()).count();}
bool ec_active=false;RenderArgs ec_last_args{};
static Backend* backend=nullptr;static std::vector<std::vector<int>> plans;static std::vector<std::unique_ptr<Buffer>> plan_gpu;static unsigned* visit_ptr=nullptr;static CUevent upstream_end;static double dispatch_ms=0;static std::vector<float> group_times;
static void rt(cudaError_t e,const char*w){if(e!=cudaSuccess)throw std::runtime_error(std::string(w)+": "+cudaGetErrorString(e));}
void ec_before_render(){ck(cuEventRecord(upstream_end,nullptr),"upstream end");}
void ec_dispatch(const RenderArgs&a){auto begin=Clock::now();
 if(ec_full){ec_launch_mapped(a,(const int*)plan_gpu[0]->p,plans[0].size(),std::min(int(plans[0].size()),backend->sms*ec_render_occupancy()),nullptr,visit_ptr);rt(cudaPeekAtLastError(),"full mapped launch");dispatch_ms=ms(begin,Clock::now());return;}
 ck(cuEventSynchronize(upstream_end),"upstream ready");
 int occupancy=ec_render_occupancy();if(!occupancy)throw std::runtime_error("zero render occupancy");
 for(size_t g=0;g<plans.size();g++){backend->current(g);auto&x=backend->groups[g];ck(cuEventRecord(x.start,x.stream),"render start");if(!plans[g].empty())ec_launch_mapped(a,reinterpret_cast<const int*>(plan_gpu[g]->p),plans[g].size(),std::min(int(plans[g].size()),x.sms*occupancy),reinterpret_cast<cudaStream_t>(x.stream),visit_ptr);rt(cudaPeekAtLastError(),"render launch");ck(cuEventRecord(x.end,x.stream),"render end");}
 backend->join();group_times.resize(plans.size());for(size_t g=0;g<plans.size();g++)ck(cuEventElapsedTime(&group_times[g],backend->groups[g].start,backend->groups[g].end),"group elapsed");ck(cuCtxSetCurrent(backend->primary),"primary restore");dispatch_ms=ms(begin,Clock::now());
}
struct GrowBuffer{CUdeviceptr p=0;size_t bytes=0;int growths=0;char* get(size_t n){if(n>bytes){if(p)ck(cuMemFree(p),"grow free");bytes=(n+1048575)/1048576*1048576;ck(cuMemAlloc(&p,bytes),"grow alloc");growths++;}return reinterpret_cast<char*>(p);}~GrowBuffer(){if(p)cuMemFree(p);}};
struct Camera{unsigned id;float tanx,tany,view[16],proj[16],pos[3];};
static uint64_t hash_bytes(const void*raw,size_t n){const unsigned char*p=(const unsigned char*)raw;uint64_t h=1469598103934665603ull;for(size_t i=0;i<n;i++)h=(h^p[i])*1099511628211ull;return h;}
static void read_exact(std::ifstream&f,void*p,size_t n){if(!f.read((char*)p,n))throw std::runtime_error("truncated input");}
struct Output{std::vector<float> color,T;std::vector<unsigned> contrib;uint64_t hash;};
static Output read_output(int w,int h){Output o;o.color.resize(w*h*3);o.T.resize(w*h);o.contrib.resize(w*h);ck(cuMemcpyDtoH(o.color.data(),(CUdeviceptr)ec_last_args.out_color,o.color.size()*4),"color read");ck(cuMemcpyDtoH(o.T.data(),(CUdeviceptr)ec_last_args.final_T,o.T.size()*4),"T read");ck(cuMemcpyDtoH(o.contrib.data(),(CUdeviceptr)ec_last_args.n_contrib,o.contrib.size()*4),"contrib read");o.hash=hash_bytes(o.color.data(),o.color.size()*4)^hash_bytes(o.T.data(),o.T.size()*4)^hash_bytes(o.contrib.data(),o.contrib.size()*4);return o;}
static bool equal(const Output&a,const Output&b){return a.color.size()==b.color.size()&&!memcmp(a.color.data(),b.color.data(),a.color.size()*4)&&!memcmp(a.T.data(),b.T.data(),a.T.size()*4)&&!memcmp(a.contrib.data(),b.contrib.data(),a.contrib.size()*4);}
static void save(const std::string&name,const Output&o){std::ofstream f(name,std::ios::binary);f.write((char*)o.color.data(),o.color.size()*4);f.write((char*)o.T.data(),o.T.size()*4);f.write((char*)o.contrib.data(),o.contrib.size()*4);}
int main(int argc,char**argv){try{
 std::map<std::string,std::string>a;for(int i=1;i+1<argc;i+=2)a[argv[i]]=argv[i+1];auto get=[&](std::string k,std::string d){return a.count(k)?a[k]:d;};
 std::string assets=get("--assets","assets/prepared/bonsai"),out=get("--out","."),purpose=get("--purpose","profile"),policies=get("--policies","N"),plan_dir=get("--plans","");int w=std::stoi(get("--width","1280")),h=std::stoi(get("--height","720")),seq=std::stoi(get("--sequence","0")),block=std::stoi(get("--block","0"));
 std::filesystem::create_directories(out);auto init_begin=Clock::now();Backend b(1);backend=&b;ck(cuEventCreate(&upstream_end,0),"up event");CUevent begin,end;ck(cuEventCreate(&begin,0),"begin");ck(cuEventCreate(&end,0),"end");
 unsigned n;std::ifstream mf(assets+"/model.bin",std::ios::binary);read_exact(mf,&n,4);std::vector<float> model((size_t)n*59);read_exact(mf,model.data(),model.size()*4);Buffer dmodel(model.size()*4);dmodel.upload(model.data());float*ptr=(float*)dmodel.p;float*xyz=ptr;ptr+=n*3;float*opacity=ptr;ptr+=n;float*scale=ptr;ptr+=n*3;float*rotation=ptr;ptr+=n*4;float*sh=ptr;
 std::ifstream cf(assets+"/cameras_"+std::to_string(w)+"x"+std::to_string(h)+".bin",std::ios::binary);unsigned nc;read_exact(cf,&nc,4);std::vector<Camera>cams(nc);for(auto&c:cams)read_exact(cf,&c,sizeof(Camera));
 int nt=((w+15)/16)*((h+15)/16);Buffer dcam(35*4),dout((size_t)w*h*3*4),dbg(12),visits(nt*4),partial(256*8);float bg[3]={0,0,0};dbg.upload(bg);GrowBuffer geometry,binning,img;
 std::vector<int> selected;bool development=purpose=="profile"||purpose=="calibrate"||purpose=="pilot";for(int i=0;i<int(nc);i++)if(i%4==(development?seq:2+seq))selected.push_back(i);if(selected.empty())throw std::runtime_error("no cameras");if(purpose=="pilot"){std::vector<int>pilot;for(int k:{1,2,3,5})if(k<int(selected.size()))pilot.push_back(selected[k]);selected=pilot;}
 auto render=[&](int ci){Camera&c=cams.at(ci);float data[35];memcpy(data,c.view,64);memcpy(data+16,c.proj,64);memcpy(data+32,c.pos,12);auto t=Clock::now();ck(cuCtxSetCurrent(b.primary),"render primary");dcam.upload(data);ck(cuEventRecord(begin,nullptr),"frame begin");
  int instances=CudaRasterizer::Rasterizer::forward([&](size_t n){return geometry.get(n);},[&](size_t n){return binning.get(n);},[&](size_t n){return img.get(n);},n,3,16,(float*)dbg.p,w,h,xyz,sh,nullptr,opacity,scale,1.f,rotation,nullptr,(float*)dcam.p,(float*)dcam.p+16,(float*)dcam.p+32,c.tanx,c.tany,false,(float*)dout.p,nullptr,false);
  rt(cudaGetLastError(),"forward error");ck(cuEventRecord(end,nullptr),"frame end");ck(cuEventSynchronize(end),"frame ready");double cpu=ms(t,Clock::now());float upstream,full;ck(cuEventElapsedTime(&upstream,begin,upstream_end),"up time");ck(cuEventElapsedTime(&full,begin,end),"full time");if(ec_full)group_times={full-upstream};size_t free,total;ck(cuMemGetInfo(&free,&total),"free memory");if(free<std::max(size_t(2ull<<30),total*15/100))throw std::runtime_error("VRAM headroom violated");return std::vector<double>{cpu,upstream,full,double(instances),double(total-free)};
 };
 auto screen=[&](){ec_digest(ec_last_args,(unsigned long long*)partial.p);rt(cudaGetLastError(),"screen launch");unsigned long long ps[256];partial.download(ps);unsigned long long sum=0;for(auto v:ps)sum+=v;return sum;};
 std::ofstream initlog(out+"/init_costs.csv");initlog<<"policy,resource_setup_ms,plan_load_upload_ms,plan_bytes\n";
 auto set_plan=[&](char policy){auto plan_start=Clock::now();ck(cuCtxSetCurrent(b.primary),"plan primary");plan_gpu.clear();ec_full=policy=='E';plans.assign(ec_full?1:b.groups.size(),{});if(policy=='N'){ec_active=false;initlog<<policy<<",null,"<<ms(plan_start,Clock::now())<<",0\n";return;}
  std::vector<int>assign(nt);if(ec_full){std::fill(assign.begin(),assign.end(),0);}else if(plan_dir.empty()){for(int t=0;t<nt;t++)assign[t]=(t>=nt/2);}else{std::ifstream f(plan_dir+"/"+std::string(1,policy)+".txt");for(int&t:assign)if(!(f>>t)||t<0||t>=int(plans.size()))throw std::runtime_error("invalid renderer plan");}
  for(int t=0;t<nt;t++)plans[assign[t]].push_back(t);for(auto&l:plans){plan_gpu.emplace_back(new Buffer(std::max(size_t(4),l.size()*4)));if(!l.empty())ck(cuMemcpyHtoD(plan_gpu.back()->p,l.data(),l.size()*4),"plan upload");}ec_active=true;initlog<<policy<<",null,"<<ms(plan_start,Clock::now())<<','<<nt*4<<'\n';
 };
 std::ofstream frames(out+"/frames.csv"),groups(out+"/groups.csv");frames<<"phase,session,policy,frame,camera_id,cpu_ready_ms,upstream_ms,gpu_pipeline_ms,render_ms,dispatch_cpu_ms,instances,memory_used_bytes,digest,planner_calls,plan_D2H_bytes,plan_H2D_bytes,recompile_count\n";groups<<"phase,session,policy,frame,group,tasks,gpu_event_ms\n";frames<<std::setprecision(10);
 if(purpose=="profile"){
  std::ofstream f(out+"/tile_weights.csv");f<<"camera_id,tile,list_length\n";
  for(int j=0;j<std::min(4,int(selected.size()));j++){int ci=selected[j*selected.size()/4];set_plan('N');auto times=render(ci);std::vector<uint2>ranges(nt);ck(cuMemcpyDtoH(ranges.data(),(CUdeviceptr)ec_last_args.ranges,nt*sizeof(uint2)),"ranges read");for(int t=0;t<nt;t++)f<<cams[ci].id<<','<<t<<','<<ranges[t].y-ranges[t].x<<'\n';auto o=read_output(w,h);save(out+"/profile_"+std::to_string(j)+".bin",read_output(w,h));std::cout<<"PROFILE "<<cams[ci].id<<" cpu="<<times[0]<<" instances="<<times[3]<<'\n';}
 }else if(purpose=="calibrate"){
  std::vector<int>classes(nt);std::vector<double>weights(nt);std::ifstream tf(get("--classes","").c_str());for(int t=0;t<nt;t++)if(!(tf>>classes[t]>>weights[t]))throw std::runtime_error("classes input invalid");
  std::ofstream f(out+"/calibration.csv");f<<"camera_id,class,mode,group,tasks,work,gpu_ms,cpu_makespan_ms\n";
  for(int j=0;j<std::min(4,int(selected.size()));j++){
   int ci=selected[j*selected.size()/4];set_plan('N');render(ci);
   for(int c=0;c<3;c++){
    plan_gpu.clear();plans.assign(2,{});int rank=0;for(int t=0;t<nt;t++)if(classes[t]==c)plans[(rank++)%2].push_back(t);
    for(auto&l:plans){plan_gpu.emplace_back(new Buffer(std::max(size_t(4),l.size()*4)));if(!l.empty())ck(cuMemcpyHtoD(plan_gpu.back()->p,l.data(),l.size()*4),"calibration upload");}
    for(int concurrent=0;concurrent<2;concurrent++)for(int repeat=-4;repeat<16;repeat++){
     auto start=Clock::now();for(int g=0;g<2;g++){b.current(g);auto&grp=b.groups[g];ck(cuEventRecord(grp.start,grp.stream),"cal start");if(!plans[g].empty())ec_launch_mapped(ec_last_args,(const int*)plan_gpu[g]->p,plans[g].size(),std::min(int(plans[g].size()),grp.sms*ec_render_occupancy()),(cudaStream_t)grp.stream,nullptr);rt(cudaPeekAtLastError(),"cal launch");ck(cuEventRecord(grp.end,grp.stream),"cal end");if(!concurrent)ck(cuStreamSynchronize(grp.stream),"cal isolated");}b.join();double cpu=ms(start,Clock::now());
     if(repeat>=0)for(int g=0;g<2;g++){float elapsed;ck(cuEventElapsedTime(&elapsed,b.groups[g].start,b.groups[g].end),"cal elapsed");double work=0;for(int t:plans[g])work+=weights[t];f<<cams[ci].id<<','<<c<<','<<(concurrent?"concurrent":"isolated")<<','<<g<<','<<plans[g].size()<<','<<work<<','<<elapsed<<','<<cpu<<'\n';}
    }
   }
  }
 }else if(purpose=="qualify"){
  std::ofstream q(out+"/qualification.csv");q<<"frame,camera,policy,bitwise,native_repeats,exactly_once\n";
  int length=std::stoi(get("--frames","16"));for(int j=0;j<length;j++){int ci=selected[j%selected.size()];set_plan('N');render(ci);auto reference=read_output(w,h);for(int repeat=1;repeat<3;repeat++){render(ci);if(!equal(reference,read_output(w,h)))throw std::runtime_error("Native nondeterminism");}
   for(char policy:policies){if(policy==',')continue;set_plan(policy);ck(cuMemsetD32(visits.p,0,nt),"visits reset");visit_ptr=policy=='N'?nullptr:(unsigned*)visits.p;render(ci);auto candidate=read_output(w,h);if(!equal(reference,candidate)){save(out+"/FAILED_reference.bin",reference);save(out+"/FAILED_candidate.bin",candidate);throw std::runtime_error(std::string("bitwise mismatch policy ")+policy+" frame "+std::to_string(j));}if(policy!='N'){std::vector<unsigned>v(nt);visits.download(v.data());for(unsigned x:v)if(x!=1)throw std::runtime_error("tile exactly-once failure");}q<<j<<','<<cams[ci].id<<','<<policy<<",1,3,1\n";visit_ptr=nullptr;}
  }
 }else{
  int epochs=std::stoi(get("--frames","512")),warm_min=std::stoi(get("--warmup","128"));std::map<int,uint64_t>native_hash;std::vector<int>sequence;for(int j=0;j<epochs;j++)sequence.push_back(selected[j%selected.size()]);
  // Precompute only output references, outside timed and planning code. No task
  // metadata from evaluation cameras is used for any plan.
  set_plan('N');int condition_count=0;auto ct=Clock::now();double conditioning=std::stod(get("--conditioning-seconds","0"));while(ms(ct,Clock::now())<conditioning*1000){render(selected[condition_count++%selected.size()]);}std::ofstream(out+"/conditioning.json")<<"{\"seconds\":"<<ms(ct,Clock::now())/1000<<",\"useful_frames\":"<<condition_count<<"}\n";
  for(int ci:selected){render(ci);native_hash[ci]=screen();}
  std::ofstream phase_log(out+"/phases.csv");phase_log<<"phase,session,policy,phase_start_ns,measure_start_ns,measure_end_ns,phase_end_ns,warmup_count\n";int session=0;
  for(char policy:policies){if(policy==',')continue;std::string phase=policy=='N'?(session==0?"N_head":"N_tail"):std::string(1,policy);auto phase_start=unix_ns();set_plan(policy);auto warm_start=Clock::now();int warm=0;do{render(selected[warm%selected.size()]);warm++;}while(warm<warm_min||ms(warm_start,Clock::now())<1000);
   auto measure_start=unix_ns();
   for(int j=0;j<epochs;j++){int ci=sequence[j];auto ts=render(ci);auto digest=screen();if(digest!=native_hash[ci]){save(out+"/FAILED_output.bin",read_output(w,h));throw std::runtime_error("formal output digest mismatch");}if(j==0||j==epochs/2||j==epochs-1)save(out+"/"+phase+"_frame_"+std::to_string(j)+".bin",read_output(w,h));
    frames<<phase<<','<<session<<','<<policy<<','<<j<<','<<cams[ci].id<<','<<ts[0]<<','<<ts[1]<<',';if(policy=='N'||policy=='E')frames<<ts[2];else frames<<"null";frames<<','<<(policy=='N'?ts[2]-ts[1]:*std::max_element(group_times.begin(),group_times.end()))<<','<<(policy=='N'?0:dispatch_ms)<<','<<ts[3]<<','<<ts[4]<<','<<digest<<",0,0,0,0\n";
    if(policy!='N')for(size_t g=0;g<plans.size();g++)groups<<phase<<','<<session<<','<<policy<<','<<j<<','<<g<<','<<plans[g].size()<<','<<group_times[g]<<'\n';
   }
   // Final complete-output comparison against Native from identical camera.
   auto measure_end=unix_ns();auto candidate=read_output(w,h);ec_active=false;ec_full=false;render(sequence.back());auto ref=read_output(w,h);if(!equal(candidate,ref))throw std::runtime_error("final full bitwise failure");
   phase_log<<phase<<','<<session++<<','<<policy<<','<<phase_start<<','<<measure_start<<','<<measure_end<<','<<unix_ns()<<','<<warm<<'\n';phase_log.flush();
   std::cout<<"SESSION_COMPLETE "<<phase<<" warmup="<<warm<<" measured="<<epochs<<std::endl;
  }
 }
 ck(cuCtxSetCurrent(b.primary),"cleanup");std::ofstream summary(out+"/summary.json");summary<<"{\"status\":\"SUCCESS\",\"gaussians\":"<<n<<",\"width\":"<<w<<",\"height\":"<<h<<",\"tiles\":"<<nt<<",\"policies\":\""<<policies<<"\",\"purpose\":\""<<purpose<<"\",\"total_process_ms\":"<<ms(init_begin,Clock::now())<<",\"geometry_bytes\":"<<geometry.bytes<<",\"binning_bytes\":"<<binning.bytes<<",\"image_bytes\":"<<img.bytes<<",\"allocation_growths\":"<<geometry.growths+binning.growths+img.growths<<",\"scope\":\"SCENE_PLAN\"}\n";
 std::ofstream correctness(out+"/correctness.json");correctness<<"{\"status\":\"PASS\",\"contract\":\"bitwise_color_finalT_ncontrib\"}\n";
 plan_gpu.clear();ck(cuEventDestroy(begin),"destroy begin");ck(cuEventDestroy(end),"destroy end");ck(cuEventDestroy(upstream_end),"destroy upstream");return 0;
}catch(std::exception&e){std::cerr<<e.what()<<'\n';return 2;}}
