#include <cuda.h>
#include <cuda_runtime.h>
#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <numeric>
#include <random>
#include <set>
#include <stdexcept>
#include <vector>
using Clock=std::chrono::steady_clock;
static void ck(cudaError_t e){if(e!=cudaSuccess)throw std::runtime_error(cudaGetErrorString(e));}
static void dc(CUresult e){if(e){const char*s;cuGetErrorString(e,&s);throw std::runtime_error(s);}}
static double ms(Clock::time_point a){return std::chrono::duration<double,std::milli>(Clock::now()-a).count();}
__host__ __device__ uint32_t mix(uint32_t x){x^=x>>16;x*=0x7feb352du;x^=x>>15;x*=0x846ca68bu;return x^(x>>16);}
__device__ unsigned smid(){unsigned x;asm volatile("mov.u32 %0, %%smid;":"=r"(x));return x;}
constexpr int WORDS=16384,THREADS=128;
struct Diagnostic{uint64_t ticks;uint32_t begin,end;};
__global__ void initialize(uint32_t* data,int count,uint32_t seed){int i=blockIdx.x*blockDim.x+threadIdx.x;if(i<count)data[i]=mix(uint32_t(i)^seed);}
template<int RECIPE,bool DIAG> __global__ void consume(const uint32_t* data,const int* ids,int first,uint32_t seed,uint2* output,Diagnostic* trace,uint32_t* hits){
 int t=ids?ids[first+blockIdx.x]:first+blockIdx.x;uint32_t odd=mix(seed+uint32_t(t)*71u)|1u,off=mix(seed^uint32_t(t)*31337u)&(WORDS-1);
 uint64_t begin=0;unsigned sm=0;if constexpr(DIAG){begin=clock64();sm=smid();}
 uint32_t sum=0,weighted=0;
 #pragma unroll 1
 for(int j=0;j<WORDS/THREADS;j++){uint32_t i=j*THREADS+threadIdx.x,x=(i*odd+off)&(WORDS-1),v;
  if constexpr(RECIPE==1){asm("ld.global.cg.u32 %0, [%1];":"=r"(v):"l"(data+size_t(t)*WORDS+x));}
  else v=data[size_t(t)*WORDS+x];sum+=v;weighted+=v*(i+1u);
 }
 for(int d=16;d;d/=2){sum+=__shfl_down_sync(0xffffffffu,sum,d);weighted+=__shfl_down_sync(0xffffffffu,weighted,d);}
 __shared__ uint2 partial[4];if(threadIdx.x%32==0)partial[threadIdx.x/32]=make_uint2(sum,weighted);__syncthreads();
 if(threadIdx.x==0){uint2 value=make_uint2(0,0);for(int w=0;w<4;w++){value.x+=partial[w].x;value.y+=partial[w].y;}output[t]=value;
  if constexpr(DIAG){trace[t]={clock64()-begin,sm,smid()};atomicAdd(hits+t,1u);}}
}
struct Resources{
 CUcontext primary;std::array<CUcontext,3> contexts;std::array<CUgreenCtx,3> green;std::array<CUstream,3> streams;
 Resources(){ck(cudaSetDevice(0));ck(cudaFree(nullptr));dc(cuCtxGetCurrent(&primary));CUdevResource all{},parts[2]{},rest{};dc(cuDeviceGetDevResource(0,&all,CU_DEV_RESOURCE_TYPE_SM));unsigned n=2;dc(cuDevSmResourceSplitByCount(parts,&n,&all,&rest,0,40));
  if(n!=2||all.sm.smCount!=84||parts[0].sm.smCount!=40||parts[1].sm.smCount!=40||rest.sm.smCount!=4)throw std::runtime_error("resource recipe mismatch");
  for(int g=0;g<3;g++){CUdevResourceDesc desc;dc(cuDevResourceGenerateDesc(&desc,g==2?&rest:&parts[g],1));dc(cuGreenCtxCreate(&green[g],desc,0,CU_GREEN_CTX_DEFAULT_STREAM));dc(cuCtxFromGreenCtx(&contexts[g],green[g]));dc(cuGreenCtxStreamCreate(&streams[g],green[g],CU_STREAM_NON_BLOCKING,0));}dc(cuCtxSetCurrent(primary));
 }
 void current(int g){dc(cuCtxSetCurrent(g<0?primary:contexts[g]));}
 void join(int g){current(g);dc(cuStreamSynchronize(streams[g]));}
 void close(){for(int g=0;g<3;g++){current(g);dc(cuStreamDestroy(streams[g]));current(-1);dc(cuGreenCtxDestroy(green[g]));}}
};
template<int RECIPE> int run(std::string dir,int tasks,int block,uint32_t seed,std::string order,bool small){
 auto process_start=Clock::now();Resources res;double context_ms=ms(process_start);cudaDeviceProp prop;ck(cudaGetDeviceProperties(&prop,0));
 size_t free,total;ck(cudaMemGetInfo(&free,&total));size_t explicit_bytes=size_t(tasks)*(WORDS*4+6*4+8+sizeof(Diagnostic)+4)+128*4;
 if(explicit_bytes>(512ull<<20)||free<explicit_bytes+std::max(size_t(2ull<<30),total*15/100))throw std::runtime_error("memory guard");
 auto init_start=Clock::now();uint32_t*data,*hits;int *tables,*batch;uint2*out;Diagnostic*trace;
 ck(cudaMalloc(&data,size_t(tasks)*WORDS*4));ck(cudaMalloc(&tables,tasks*6*4));ck(cudaMalloc(&batch,128*4));ck(cudaMalloc(&out,tasks*sizeof(uint2)));ck(cudaMalloc(&trace,tasks*sizeof(Diagnostic)));ck(cudaMalloc(&hits,tasks*4));
 ck(cudaMemset(hits,0,tasks*4));ck(cudaMemset(out,0,tasks*sizeof(uint2)));ck(cudaMemset(trace,0,tasks*sizeof(Diagnostic)));initialize<<<(tasks*WORDS+255)/256,256>>>(data,tasks*WORDS,seed);ck(cudaGetLastError());ck(cudaDeviceSynchronize());double allocation_init_ms=ms(init_start);
 auto ref_start=Clock::now();std::vector<uint2> expected(tasks,make_uint2(0,0)),actual(tasks);std::vector<Diagnostic> hosttrace(tasks);std::vector<uint32_t> hosthits(tasks);
 // Independent reference traverses physical logical words in order and inverts the permutation.
 for(int t=0;t<tasks;t++){uint32_t odd=mix(seed+uint32_t(t)*71u)|1u,off=mix(seed^uint32_t(t)*31337u)&(WORDS-1),inv=odd;for(int k=0;k<5;k++)inv*=2u-odd*inv;
  if((odd*inv)!=1u)throw std::runtime_error("inverse check");for(uint32_t x=0;x<WORDS;x++){uint32_t v=mix(uint32_t(t*WORDS+x)^seed),i=((x-off)*inv)&(WORDS-1);expected[t].x+=v;expected[t].y+=v*(i+1u);}}
 double cpu_reference_ms=ms(ref_start);{std::ofstream f(dir+"/expected_uint2.bin",std::ios::binary);f.write((char*)expected.data(),tasks*sizeof(uint2));}
 auto check=[&](){res.current(-1);ck(cudaMemcpy(actual.data(),out,tasks*sizeof(uint2),cudaMemcpyDeviceToHost));for(int t=0;t<tasks;t++)if(actual[t].x!=expected[t].x||actual[t].y!=expected[t].y)throw std::runtime_error("full CPU output mismatch");};
 auto launch=[&](bool diag,const int*table,int first,int count,int g){if(!count)return;res.current(g);cudaStream_t s=g<0?0:(cudaStream_t)res.streams[g];if(diag)consume<RECIPE,true><<<count,128,0,s>>>(data,table,first,seed,out,trace,hits);else consume<RECIPE,false><<<count,128,0,s>>>(data,table,first,seed,out,trace,hits);ck(cudaGetLastError());};
 std::array<std::set<unsigned>,3> observed;
 std::ofstream cal(dir+"/GROUP_REGION_CALIBRATION.csv");cal<<"round,group,task,ticks,sm_begin,sm_end,words\n";
 auto cal_start=Clock::now();std::vector<std::array<double,3>> costs(tasks);double max_diagnostic_gpu_ms=0;
 for(int round=0;round<4;round++){std::vector<int> ids(tasks);std::iota(ids.begin(),ids.end(),0);std::mt19937 rng(seed+round*977u);std::shuffle(ids.begin(),ids.end(),rng);
  for(int offset=0;offset<tasks;offset+=128){int count=std::min(128,tasks-offset);res.current(-1);ck(cudaMemcpy(batch,ids.data()+offset,count*4,cudaMemcpyHostToDevice));ck(cudaDeviceSynchronize());
   for(int turn=0;turn<3;turn++){int g=(turn+round)%3;res.current(-1);ck(cudaMemset(trace,255,tasks*sizeof(Diagnostic)));ck(cudaDeviceSynchronize());res.current(g);cudaEvent_t a,z;ck(cudaEventCreate(&a));ck(cudaEventCreate(&z));ck(cudaEventRecord(a,(cudaStream_t)res.streams[g]));launch(true,batch,0,count,g);ck(cudaEventRecord(z,(cudaStream_t)res.streams[g]));res.join(g);float elapsed;ck(cudaEventElapsedTime(&elapsed,a,z));max_diagnostic_gpu_ms=std::max(max_diagnostic_gpu_ms,double(elapsed));ck(cudaEventDestroy(a));ck(cudaEventDestroy(z));res.current(-1);
    if(elapsed>20)throw std::runtime_error("diagnostic kernel exceeds 20ms guard");ck(cudaMemcpy(hosttrace.data(),trace,tasks*sizeof(Diagnostic),cudaMemcpyDeviceToHost));ck(cudaMemcpy(actual.data(),out,tasks*sizeof(uint2),cudaMemcpyDeviceToHost));
    for(int i=offset;i<offset+count;i++){int t=ids[i];auto d=hosttrace[t];if(!d.ticks||d.begin!=d.end||actual[t].x!=expected[t].x||actual[t].y!=expected[t].y)throw std::runtime_error("calibration correctness or migration");observed[g].insert(d.begin);costs[t][g]+=std::log(double(d.ticks))/4;cal<<round<<','<<g<<','<<t<<','<<d.ticks<<','<<d.begin<<','<<d.end<<','<<WORDS<<'\n';}
   }
  }
 }
 cal.close();double calibration_ms=ms(cal_start);for(int a=0;a<3;a++)for(int b=a+1;b<3;b++)for(auto sm:observed[a])if(observed[b].count(sm))throw std::runtime_error("overlapping observed groups");
 auto plan_start=Clock::now();int quota=tasks*40/84;std::array<int,4> bounds{0,quota,2*quota,tasks};std::array<std::vector<int>,6> plans;
 plans[0].resize(tasks);std::iota(plans[0].begin(),plans[0].end(),0);plans[1]=plans[0];std::mt19937 blind(seed^2026101310u);std::shuffle(plans[1].begin(),plans[1].end(),blind);
 std::array<double,3> group_mean{};for(auto v:costs)for(int g=0;g<3;g++)group_mean[g]+=v[g]/tasks;
 std::vector<int> exchange(plans[1].begin(),plans[1].begin()+2*quota);std::sort(exchange.begin(),exchange.end(),[&](int a,int b){double da=(costs[a][0]-group_mean[0])-(costs[a][1]-group_mean[1]),db=(costs[b][0]-group_mean[0])-(costs[b][1]-group_mean[1]);return da==db?a<b:da<db;});
 plans[2]=exchange;plans[2].insert(plans[2].end(),plans[1].begin()+2*quota,plans[1].end());plans[3]=plans[2];for(int i=0;i<quota;i++)std::swap(plans[3][i],plans[3][quota+i]);
 for(int p=4;p<6;p++){plans[p]=plans[2];std::mt19937 rng(p==4?2026101312u:2026101313u);std::shuffle(plans[p].begin(),plans[p].begin()+2*quota,rng);}
 std::ofstream plan(dir+"/plans.csv"),placement(dir+"/placement.csv"),quality(dir+"/quality.csv"),timefile(dir+"/timings.csv");plan<<"policy,index,task,planned_group\n";placement<<"phase,policy,task,planned_group,sm_begin,sm_end,expected_group_observed\n";quality<<"phase,policy,output_errors,ownership_errors,group_unknown,group_mismatch\n";timefile<<"block,policy,repeat,cpu_ready_ms,tasks,logical_words,planner_calls,schedule_H2D_bytes,schedule_D2H_bytes\n";
 for(int p=0;p<6;p++){if(p)for(int g=0;g<3;g++)std::sort(plans[p].begin()+bounds[g],plans[p].begin()+bounds[g+1]);auto sorted=plans[p];std::sort(sorted.begin(),sorted.end());for(int i=0;i<tasks;i++)if(sorted[i]!=i)throw std::runtime_error("plan not bijective");ck(cudaMemcpy(tables+p*tasks,plans[p].data(),tasks*4,cudaMemcpyHostToDevice));for(int i=0;i<tasks;i++)plan<<p<<','<<i<<','<<plans[p][i]<<','<<(p?i<quota?0:i<2*quota?1:2:-1)<<'\n';}
 ck(cudaDeviceSynchronize());plan.close();double plan_ms=ms(plan_start);
 auto epoch=[&](int policy,bool diag){if(policy==0){launch(diag,nullptr,0,tasks,-1);ck(cudaDeviceSynchronize());}else{for(int g=0;g<3;g++)launch(diag,tables+policy*tasks,bounds[g],bounds[g+1]-bounds[g],g);for(int g=0;g<3;g++)res.join(g);res.current(-1);}};
 int unknown=0,mismatch=0;
 auto audit=[&](int policy,std::string phase){res.current(-1);ck(cudaMemset(hits,0,tasks*4));ck(cudaMemset(trace,255,tasks*sizeof(Diagnostic)));ck(cudaDeviceSynchronize());epoch(policy,true);check();ck(cudaMemcpy(hosttrace.data(),trace,tasks*sizeof(Diagnostic),cudaMemcpyDeviceToHost));ck(cudaMemcpy(hosthits.data(),hits,tasks*4,cudaMemcpyDeviceToHost));int bad=0,u=0,m=0;for(int i=0;i<tasks;i++){int t=plans[policy][i],g=policy?i<quota?0:i<2*quota?1:2:-1;auto d=hosttrace[t];bad+=hosthits[t]!=1||d.begin!=d.end;bool match=g<0||observed[g].count(d.begin);if(!match){int found=-1;for(int k=0;k<3;k++)if(observed[k].count(d.begin))found=k;if(found<0)u++;else m++;}placement<<phase<<','<<policy<<','<<t<<','<<g<<','<<d.begin<<','<<d.end<<','<<match<<'\n';}quality<<phase<<','<<policy<<",0,"<<bad<<','<<u<<','<<m<<'\n';if(bad)throw std::runtime_error("ownership or migration failure");unknown+=u;mismatch+=m;};
 // Same-context event qualification; submit all independent Green work before joining.
 for(int policy=0;policy<6;policy++){audit(policy,"before");std::array<cudaEvent_t,3>a,z;int groups=policy?3:1;for(int g=0;g<groups;g++){res.current(policy?g:-1);ck(cudaEventCreate(&a[g]));ck(cudaEventCreate(&z[g]));cudaStream_t s=policy?(cudaStream_t)res.streams[g]:0;ck(cudaEventRecord(a[g],s));launch(false,policy?tables+policy*tasks:nullptr,policy?bounds[g]:0,policy?bounds[g+1]-bounds[g]:tasks,policy?g:-1);ck(cudaEventRecord(z[g],s));}for(int g=0;g<groups;g++){res.current(policy?g:-1);ck(cudaEventSynchronize(z[g]));float elapsed;ck(cudaEventElapsedTime(&elapsed,a[g],z[g]));max_diagnostic_gpu_ms=std::max(max_diagnostic_gpu_ms,double(elapsed));ck(cudaEventDestroy(a[g]));ck(cudaEventDestroy(z[g]));if(elapsed>20)throw std::runtime_error("qualification kernel exceeds 20ms guard");}res.current(-1);check();}
 if(!small)for(char pc:order){int policy=pc-'0';for(int k=0;k<32;k++)epoch(policy,false);check();for(int repeat=0;repeat<128;repeat++){auto begin=Clock::now();epoch(policy,false);double elapsed=ms(begin);timefile<<block<<','<<policy<<','<<repeat<<','<<elapsed<<','<<tasks<<','<<size_t(tasks)*WORDS<<",0,0,0\n";check();if(elapsed>20)throw std::runtime_error("CPU epoch exceeds 20ms guard");}{std::ofstream f(dir+"/output_policy"+std::to_string(policy)+".bin",std::ios::binary);f.write((char*)actual.data(),tasks*sizeof(uint2));}audit(policy,"after");}
 std::ofstream groups(dir+"/groups.csv");groups<<"group,smid\n";for(int g=0;g<3;g++)for(auto sm:observed[g])groups<<g<<','<<sm<<'\n';
 std::ofstream meta(dir+"/metadata.json");meta<<"{\"tasks\":"<<tasks<<",\"seed\":"<<seed<<",\"block\":"<<block<<",\"recipe\":"<<RECIPE<<",\"quota\":["<<quota<<','<<quota<<','<<tasks-2*quota<<"],\"explicit_GPU_bytes\":"<<explicit_bytes<<",\"observed_group_SM_counts\":["<<observed[0].size()<<','<<observed[1].size()<<','<<observed[2].size()<<"],\"group_unknown\":"<<unknown<<",\"group_mismatch\":"<<mismatch<<",\"context_ms\":"<<context_ms<<",\"allocation_init_ms\":"<<allocation_init_ms<<",\"cpu_reference_ms\":"<<cpu_reference_ms<<",\"calibration_ms\":"<<calibration_ms<<",\"plan_ms\":"<<plan_ms<<",\"max_diagnostic_kernel_ms\":"<<max_diagnostic_gpu_ms<<",\"formal_diagnostics\":false,\"output_errors\":0}\n";
 for(void*p:{(void*)data,(void*)tables,(void*)batch,(void*)out,(void*)trace,(void*)hits})ck(cudaFree(p));res.close();std::cout<<"PASS tasks="<<tasks<<" max_diagnostic_ms="<<max_diagnostic_gpu_ms<<" unknown="<<unknown<<" mismatch="<<mismatch<<'\n';return 0;
}
int main(int argc,char**argv){try{if(argc!=8)throw std::runtime_error("causal out tasks block seed recipe order mode");std::filesystem::create_directories(argv[1]);int recipe=std::stoi(argv[5]);return recipe?run<1>(argv[1],std::stoi(argv[2]),std::stoi(argv[3]),std::stoul(argv[4]),argv[6],std::string(argv[7])=="qualify"):run<0>(argv[1],std::stoi(argv[2]),std::stoi(argv[3]),std::stoul(argv[4]),argv[6],std::string(argv[7])=="qualify");}catch(std::exception&e){std::cerr<<"ERROR: "<<e.what()<<'\n';return 2;}}
