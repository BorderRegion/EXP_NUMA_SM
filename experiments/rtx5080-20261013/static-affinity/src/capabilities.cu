#include <cuda.h>
#include <cuda_runtime.h>
#include <cooperative_groups.h>
#include <iostream>
#include <vector>
#include <set>
#include <stdexcept>
static void ck(cudaError_t e){if(e!=cudaSuccess)throw std::runtime_error(cudaGetErrorString(e));}
static void dc(CUresult e){if(e!=CUDA_SUCCESS){const char*s;cuGetErrorString(e,&s);throw std::runtime_error(s);}}
__device__ unsigned smid(){unsigned x;asm("mov.u32 %0, %%smid;":"=r"(x));return x;}
__global__ void observe(unsigned* out){unsigned x=threadIdx.x+blockIdx.x;for(int i=0;i<2048;i++)x=x*1664525u+1013904223u;if(!threadIdx.x){out[blockIdx.x*2]=smid();out[blockIdx.x*2+1]=x;}}
__global__ void cooperative(unsigned* out){auto grid=cooperative_groups::this_grid();if(!threadIdx.x)out[blockIdx.x]=smid();grid.sync();if(!threadIdx.x)out[gridDim.x+blockIdx.x]=out[(blockIdx.x+1)%gridDim.x];}
int main(){try{dc(cuInit(0));ck(cudaSetDevice(0));ck(cudaFree(nullptr));cudaDeviceProp p;ck(cudaGetDeviceProperties(&p,0));int coop,driver,runtime;ck(cudaDeviceGetAttribute(&coop,cudaDevAttrCooperativeLaunch,0));ck(cudaDriverGetVersion(&driver));ck(cudaRuntimeGetVersion(&runtime));
std::cout<<"{\"name\":\""<<p.name<<"\",\"sm_count\":"<<p.multiProcessorCount<<",\"l2_bytes\":"<<p.l2CacheSize<<",\"cc_major\":"<<p.major<<",\"cc_minor\":"<<p.minor<<",\"driver_api\":"<<driver<<",\"runtime\":"<<runtime<<",\"cooperative_attribute\":"<<coop;
unsigned* out;ck(cudaMalloc(&out,8192));std::vector<unsigned> host(2048);
if(coop){int occ;ck(cudaOccupancyMaxActiveBlocksPerMultiprocessor(&occ,cooperative,32,0));int blocks=std::min(84,p.multiProcessorCount*occ);void* args[]={&out};ck(cudaLaunchCooperativeKernel((void*)cooperative,blocks,32,args));ck(cudaDeviceSynchronize());ck(cudaMemcpy(host.data(),out,blocks*8,cudaMemcpyDeviceToHost));for(int i=0;i<blocks;i++)if(host[blocks+i]!=host[(i+1)%blocks])throw std::runtime_error("cooperative barrier output mismatch");std::set<unsigned> sm(host.begin(),host.begin()+blocks);std::cout<<",\"cooperative_sm_coverage\":"<<sm.size()<<",\"cooperative_output_correct\":true";}
CUdevResource all{},parts[2]{},rem{};CUresult result=cuDeviceGetDevResource(0,&all,CU_DEV_RESOURCE_TYPE_SM);std::cout<<",\"resource_query_result\":"<<result;
if(result==CUDA_SUCCESS){unsigned n=2;result=cuDevSmResourceSplitByCount(parts,&n,&all,&rem,0,(all.sm.smCount/2/all.sm.smCoscheduledAlignment)*all.sm.smCoscheduledAlignment);std::cout<<",\"sm_resource_count\":"<<all.sm.smCount<<",\"minimum_partition\":"<<all.sm.minSmPartitionSize<<",\"coscheduled_alignment\":"<<all.sm.smCoscheduledAlignment<<",\"split_result\":"<<result<<",\"split_groups\":"<<n<<",\"remainder_sm_count\":"<<rem.sm.smCount<<",\"groups\":[";
if(result==CUDA_SUCCESS)for(unsigned g=0;g<n;g++){if(g)std::cout<<',';CUdevResourceDesc desc;dc(cuDevResourceGenerateDesc(&desc,&parts[g],1));CUgreenCtx ctx;CUresult create=cuGreenCtxCreate(&ctx,desc,0,CU_GREEN_CTX_DEFAULT_STREAM);std::cout<<"{\"id\":"<<g<<",\"provisioned_sms\":"<<parts[g].sm.smCount<<",\"create_result\":"<<create;
if(create==CUDA_SUCCESS){CUcontext converted;dc(cuCtxFromGreenCtx(&converted,ctx));CUstream stream;dc(cuGreenCtxStreamCreate(&stream,ctx,CU_STREAM_NON_BLOCKING,0));observe<<<336,32,0,(cudaStream_t)stream>>>(out);ck(cudaGetLastError());dc(cuStreamSynchronize(stream));ck(cudaMemcpy(host.data(),out,336*8,cudaMemcpyDeviceToHost));std::set<unsigned> ids;for(int i=0;i<336;i++)ids.insert(host[i*2]);std::cout<<",\"observed_sms\":[";bool first=true;for(auto s:ids){if(!first)std::cout<<',';std::cout<<s;first=false;}std::cout<<']';dc(cuStreamDestroy(stream));dc(cuGreenCtxDestroy(ctx));}std::cout<<'}';}
std::cout<<']';}std::cout<<"}\n";ck(cudaFree(out));return 0;}catch(std::exception&e){std::cerr<<"ERROR: "<<e.what()<<'\n';return 2;}}
