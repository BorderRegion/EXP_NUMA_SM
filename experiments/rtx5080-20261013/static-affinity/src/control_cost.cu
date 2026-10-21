#include <cuda.h>
#include <cuda_runtime.h>
#include <cooperative_groups.h>
#include <vector>
#include <array>
#include <algorithm>
#include <numeric>
#include <random>
#include <fstream>
#include <iostream>
#include <chrono>
#include <stdexcept>
#include <filesystem>
using Clock=std::chrono::steady_clock;
static CUcontext primary_ctx;static std::array<CUcontext,3> green_contexts;
static void ck(cudaError_t e){if(e!=cudaSuccess)throw std::runtime_error(cudaGetErrorString(e));}
static void dc(CUresult e){if(e){const char*s;cuGetErrorString(e,&s);throw std::runtime_error(s);}}
__device__ unsigned smid(){unsigned s;asm("mov.u32 %0, %%smid;":"=r"(s));return s;}
__host__ __device__ uint32_t value(uint32_t x){return (x^0x9e3779b9u)*1664525u+1013904223u;}
__global__ void initialize(uint32_t* x,int n){int i=blockIdx.x*blockDim.x+threadIdx.x;if(i<n)x[i]=value(i);}
__device__ void task(int t,const uint32_t* data,int words,uint32_t* out,uint32_t* visits,uint32_t* positions,bool diagnostic){
    uint32_t sum=0;for(int j=0;j<16;j++)sum+=data[(t*131u+threadIdx.x*1021u+j*7919u)&(words-1)];
    for(int d=16;d;d/=2)sum+=__shfl_down_sync(0xffffffffu,sum,d);
    __shared__ uint32_t partial[4];if(threadIdx.x%32==0)partial[threadIdx.x/32]=sum;__syncthreads();
    if(threadIdx.x==0){out[t]=partial[0]+partial[1]+partial[2]+partial[3];positions[t]=smid();if(diagnostic)atomicAdd(visits+t,1u);}__syncthreads();
}
template<int MODE,int N> __global__ void direct(const uint32_t* data,int words,const uint32_t* ids,int first,uint32_t* out,uint32_t* visits,uint32_t* positions,bool diagnostic){int at=first+blockIdx.x;int t=MODE==0?at:MODE==1?ids[at]:(at*17)&(N-1);task(t,data,words,out,visits,positions,diagnostic);}
template<int MODE,int N> __global__ void roster(const uint32_t* data,int words,const uint32_t* ids,const int* bounds,const int* sm_group,int* members,uint32_t* out,uint32_t* visits,uint32_t* positions,bool diagnostic,int forced){
    auto grid=cooperative_groups::this_grid();unsigned sm=smid();if(!threadIdx.x)members[blockIdx.x]=forced>=0?forced:sm<256&&sm_group[sm]>=0?sm_group[sm]:0;grid.sync();
    __shared__ int mine,rank,count,target[3];
    if(!threadIdx.x){mine=members[blockIdx.x];int counts[3]={0,0,0},active[3],n=0;rank=0;for(int w=0;w<gridDim.x;w++){int g=members[w];counts[g]++;if(w<blockIdx.x&&g==mine)rank++;}for(int g=0;g<3;g++)if(counts[g])active[n++]=g;count=counts[mine];for(int g=0;g<3;g++)target[g]=counts[g]?g:active[g%n];}__syncthreads();
    for(int g=0;g<3;g++)if(target[g]==mine)for(int at=bounds[g]+rank;at<bounds[g+1];at+=count){int t=MODE==0?at:MODE==1?ids[at]:(at*17)&(N-1);task(t,data,words,out,visits,positions,diagnostic);}
}
template<int MODE,int N> void call(int backend,int blocks,int workers,const uint32_t* data,int words,const uint32_t* ids,const int* bounds,const int* groups,int* members,uint32_t* out,uint32_t* visits,uint32_t* positions,bool diag,int forced,const std::array<CUstream,3>& streams,const std::array<int,4>& offsets){
    if(backend==0){direct<MODE,N><<<N,128>>>(data,words,ids,0,out,visits,positions,diag);ck(cudaGetLastError());ck(cudaDeviceSynchronize());}
    if(backend==1){for(int g=0;g<3;g++){int first=offsets[g],count=offsets[g+1]-first;dc(cuCtxSetCurrent(green_contexts[g]));if(count)direct<MODE,N><<<count,128,0,(cudaStream_t)streams[g]>>>(data,words,ids,first,out,visits,positions,diag);}ck(cudaGetLastError());for(int g=0;g<3;g++){dc(cuCtxSetCurrent(green_contexts[g]));dc(cuStreamSynchronize(streams[g]));}dc(cuCtxSetCurrent(primary_ctx));}
    if(backend==2){void* args[]={&data,&words,&ids,&bounds,&groups,&members,&out,&visits,&positions,&diag,&forced};ck(cudaLaunchCooperativeKernel((void*)roster<MODE,N>,workers,128,args));ck(cudaDeviceSynchronize());}
}
template<int N> int run(const std::string& dir,int block,bool small){
    ck(cudaSetDevice(0));ck(cudaFree(nullptr));dc(cuCtxGetCurrent(&primary_ctx));cudaDeviceProp prop;ck(cudaGetDeviceProperties(&prop,0));int support;ck(cudaDeviceGetAttribute(&support,cudaDevAttrCooperativeLaunch,0));if(!support)throw std::runtime_error("cooperative unsupported");
    auto init=Clock::now();int words=small?16384:1<<22;uint32_t *data,*ids,*out,*visits,*positions;int *bounds,*groups,*members;
    ck(cudaMalloc(&data,words*4));ck(cudaMalloc(&ids,N*4));ck(cudaMalloc(&out,N*4));ck(cudaMalloc(&visits,N*4));ck(cudaMalloc(&positions,N*4));ck(cudaMalloc(&bounds,16));ck(cudaMalloc(&groups,1024));ck(cudaMalloc(&members,prop.multiProcessorCount*4));
    initialize<<<(words+255)/256,256>>>(data,words);ck(cudaDeviceSynchronize());std::vector<uint32_t> table(N);for(int i=0;i<N;i++)table[i]=(i*17)&(N-1);auto sorted=table;std::sort(sorted.begin(),sorted.end());for(int i=0;i<N;i++)if(sorted[i]!=i)throw std::runtime_error("table not bijective");ck(cudaMemcpy(ids,table.data(),N*4,cudaMemcpyHostToDevice));
    CUdevResource all{},part[2]{},remain{};dc(cuDeviceGetDevResource(0,&all,CU_DEV_RESOURCE_TYPE_SM));unsigned count=2;dc(cuDevSmResourceSplitByCount(part,&count,&all,&remain,0,(all.sm.smCount/2/all.sm.smCoscheduledAlignment)*all.sm.smCoscheduledAlignment));if(count!=2||!remain.sm.smCount)throw std::runtime_error("registered 2 groups plus remainder recipe unavailable");
    std::array<CUgreenCtx,3> contexts;std::array<CUstream,3> streams;std::array<int,4> offsets{0,int(N*part[0].sm.smCount/all.sm.smCount),int(N*(part[0].sm.smCount+part[1].sm.smCount)/all.sm.smCount),N};
    for(int g=0;g<3;g++){CUdevResourceDesc desc;dc(cuDevResourceGenerateDesc(&desc,g==2?&remain:&part[g],1));dc(cuGreenCtxCreate(&contexts[g],desc,0,CU_GREEN_CTX_DEFAULT_STREAM));dc(cuCtxFromGreenCtx(&green_contexts[g],contexts[g]));dc(cuGreenCtxStreamCreate(&streams[g],contexts[g],CU_STREAM_NON_BLOCKING,0));}
    ck(cudaMemcpy(bounds,offsets.data(),16,cudaMemcpyHostToDevice));std::vector<uint32_t> expected(N),host(N),seen(N),where(N);for(int t=0;t<N;t++)for(int lane=0;lane<128;lane++)for(int j=0;j<16;j++)expected[t]+=value((t*131u+lane*1021u+j*7919u)&(words-1));
    int workers=prop.multiProcessorCount;int occ;ck(cudaOccupancyMaxActiveBlocksPerMultiprocessor(&occ,roster<1,N>,128,0));if(workers>occ*prop.multiProcessorCount)throw std::runtime_error("cooperative capacity guard");
    std::vector<int> group(256,-1);std::ofstream placement(dir+"/placement.csv"),quality(dir+"/quality.csv"),frames(dir+"/timings.csv");placement<<"group,smid\n";quality<<"backend,mode,forced_group,missed_or_duplicate,output_errors\n";frames<<"block,backend,mode,repeat,cpu_ready_ms,gpu_span_ms,tasks,workers,planner_calls,schedule_D2H,schedule_H2D,roster_grid_barriers\n";
    auto launch=[&](int backend,int mode,bool diag,int forced){if(mode==0)call<0,N>(backend,N,workers,data,words,ids,bounds,groups,members,out,visits,positions,diag,forced,streams,offsets);if(mode==1)call<1,N>(backend,N,workers,data,words,ids,bounds,groups,members,out,visits,positions,diag,forced,streams,offsets);if(mode==2)call<2,N>(backend,N,workers,data,words,ids,bounds,groups,members,out,visits,positions,diag,forced,streams,offsets);};
    launch(1,0,false,-1);ck(cudaMemcpy(where.data(),positions,N*4,cudaMemcpyDeviceToHost));for(int g=0;g<3;g++)for(int t=offsets[g];t<offsets[g+1];t++){int sm=where[t];if(sm>=256||(group[sm]>=0&&group[sm]!=g))throw std::runtime_error("overlapping observed partitions");group[sm]=g;}
    for(int sm=0;sm<256;sm++)if(group[sm]>=0)placement<<group[sm]<<','<<sm<<'\n';ck(cudaMemcpy(groups,group.data(),1024,cudaMemcpyHostToDevice));
    double initialization=std::chrono::duration<double,std::milli>(Clock::now()-init).count();
    for(int backend=0;backend<3;backend++)for(int mode=0;mode<3;mode++)for(int forced=-1;forced<(backend==2?3:0);forced++){ck(cudaMemset(visits,0,N*4));launch(backend,mode,true,forced);ck(cudaMemcpy(host.data(),out,N*4,cudaMemcpyDeviceToHost));ck(cudaMemcpy(seen.data(),visits,N*4,cudaMemcpyDeviceToHost));int bad=0,wrong=0;for(int i=0;i<N;i++){bad+=seen[i]!=1;wrong+=host[i]!=expected[i];}quality<<backend<<','<<mode<<','<<forced<<','<<bad<<','<<wrong<<'\n';if(bad||wrong)throw std::runtime_error("control ownership/output mismatch");}
    if(!small){std::vector<int> order(9);std::iota(order.begin(),order.end(),0);std::mt19937 rng(2026101303u);std::shuffle(order.begin(),order.end(),rng);std::rotate(order.begin(),order.begin()+block%9,order.end());cudaEvent_t begin,end;ck(cudaEventCreate(&begin));ck(cudaEventCreate(&end));for(int policy:order){int backend=policy/3,mode=policy%3;for(int i=0;i<32;i++)launch(backend,mode,false,-1);for(int repeat=0;repeat<128;repeat++){auto a=Clock::now();ck(cudaEventRecord(begin));ck(cudaEventSynchronize(begin));launch(backend,mode,false,-1);ck(cudaEventRecord(end));ck(cudaEventSynchronize(end));double cpu=std::chrono::duration<double,std::milli>(Clock::now()-a).count();float ms;ck(cudaEventElapsedTime(&ms,begin,end));frames<<block<<','<<backend<<','<<mode<<','<<repeat<<','<<cpu<<','<<ms<<','<<N<<','<<workers<<",0,0,0,"<<(backend==2?1:0)<<'\n';if(ms>20)throw std::runtime_error("control timing exceeds guard");}ck(cudaMemcpy(host.data(),out,N*4,cudaMemcpyDeviceToHost));if(host!=expected)throw std::runtime_error("timed output mismatch");}}
    std::ofstream meta(dir+"/control.json");meta<<"{\"tasks\":"<<N<<",\"workers\":"<<workers<<",\"occupancy_limit_blocks_per_sm\":"<<occ<<",\"partition_sm_counts\":["<<part[0].sm.smCount<<','<<part[1].sm.smCount<<','<<remain.sm.smCount<<"],\"initialization_ms_including_CPU_reference\":"<<initialization<<",\"plan_table_bytes\":"<<N*4<<",\"grid_barriers_per_roster_launch\":1,\"affinity_map_used\":false,\"errors\":0}\n";
    for(int g=0;g<3;g++){dc(cuCtxSetCurrent(green_contexts[g]));dc(cuStreamDestroy(streams[g]));dc(cuCtxSetCurrent(primary_ctx));dc(cuGreenCtxDestroy(contexts[g]));}for(void*p:{(void*)data,(void*)ids,(void*)out,(void*)visits,(void*)positions,(void*)bounds,(void*)groups,(void*)members})ck(cudaFree(p));std::cout<<"CONTROL PASS tasks="<<N<<"\n";return 0;
}
int main(int argc,char**argv){try{if(argc!=4)throw std::runtime_error("control_cost out_dir block mode");std::filesystem::create_directories(argv[1]);return std::string(argv[3])=="small"?run<32>(argv[1],std::stoi(argv[2]),true):run<4096>(argv[1],std::stoi(argv[2]),false);}catch(std::exception&e){std::cerr<<"ERROR: "<<e.what()<<'\n';return 2;}}
