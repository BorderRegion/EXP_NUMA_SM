#include "/home/ubuntu/projects/leetgpu-lab/.venv/lib/python3.12/site-packages/nvidia/cuda_runtime/include/cuda.h"
#include <cuda_runtime.h>
#include <vector>
#include <string>
#include <stdexcept>
#include <chrono>
#include <cstdint>
#include <algorithm>
static thread_local std::string error;
void ck(CUresult x,const char*s){if(x){const char*p=nullptr;cuGetErrorString(x,&p);throw std::runtime_error(std::string(s)+": "+(p?p:"unknown"));}}
#define TRY try
#define CATCH catch(std::exception&e){error=e.what();return -1;}
extern "C" const char*gc_error(){return error.c_str();}
struct Resource{CUgreenCtx green=nullptr;CUcontext ctx=nullptr;CUstream stream=nullptr;};
static CUdevice dev;static CUcontext primary;static std::vector<CUdevResource> units;static std::vector<Resource> groups;
extern "C" int gc_init(){TRY{ck(cuInit(0),"init");ck(cuDeviceGet(&dev,0),"device");ck(cuDevicePrimaryCtxRetain(&primary,dev),"primary");ck(cuCtxSetCurrent(primary),"set primary");CUdevResource all{},rem{};ck(cuDeviceGetDevResource(dev,&all,CU_DEV_RESOURCE_TYPE_SM),"get SM resources");unsigned n=0;ck(cuDevSmResourceSplitByCount(nullptr,&n,&all,nullptr,0,2),"simulate split");if(n!=28)throw std::runtime_error("Not 28 two-SM resources");units.resize(n);ck(cuDevSmResourceSplitByCount(units.data(),&n,&all,&rem,0,2),"split");Resource p;p.ctx=primary;ck(cuStreamCreate(&p.stream,CU_STREAM_NON_BLOCKING),"primary stream");groups.push_back(p);return n;}CATCH}
extern "C" int gc_create(const int*ids,int n){TRY{std::vector<CUdevResource> r;for(int i=0;i<n;i++)r.push_back(units.at(ids[i]));CUdevResourceDesc d;ck(cuDevResourceGenerateDesc(&d,r.data(),r.size()),"merge descriptor");Resource g;ck(cuGreenCtxCreate(&g.green,d,dev,CU_GREEN_CTX_DEFAULT_STREAM),"green create");ck(cuCtxFromGreenCtx(&g.ctx,g.green),"green context");ck(cuCtxSetCurrent(g.ctx),"green current");ck(cuGreenCtxStreamCreate(&g.stream,g.green,CU_STREAM_NON_BLOCKING,0),"green stream");groups.push_back(g);ck(cuCtxSetCurrent(primary),"restore primary");return groups.size()-1;}CATCH}
extern "C" unsigned long long gc_stream(int id){return (unsigned long long)groups.at(id).stream;}
extern "C" int gc_current(int id){TRY{ck(cuCtxSetCurrent(groups.at(id).ctx),"current");return 0;}CATCH}
extern "C" int gc_sync(int id){TRY{ck(cuStreamSynchronize(groups.at(id).stream),"sync");return 0;}CATCH}
extern "C" int gc_destroy(int id){TRY{auto&g=groups.at(id);ck(cuCtxSetCurrent(g.ctx),"destroy current");ck(cuStreamSynchronize(g.stream),"destroy sync");ck(cuStreamDestroy(g.stream),"destroy stream");g.stream=nullptr;ck(cuCtxSetCurrent(primary),"restore primary");if(g.green)ck(cuGreenCtxDestroy(g.green),"destroy green");g.green=nullptr;g.ctx=nullptr;return 0;}CATCH}
__global__ void position(unsigned* out,int rounds){unsigned sm0,sm1;asm volatile("mov.u32 %0, %%smid;":"=r"(sm0));float v=threadIdx.x+blockIdx.x+1.0f;for(int i=0;i<rounds;i++)v=fmaf(v,1.00001f,0.01f);asm volatile("mov.u32 %0, %%smid;":"=r"(sm1));if(threadIdx.x==0){out[blockIdx.x*3]=sm0;out[blockIdx.x*3+1]=sm1;out[blockIdx.x*3+2]=__float_as_uint(v);}}
extern "C" int gc_position(int id,void*out,int grid){TRY{auto&g=groups.at(id);ck(cuCtxSetCurrent(g.ctx),"position current");position<<<grid,128,0,(cudaStream_t)g.stream>>>((unsigned*)out,512);auto e=cudaGetLastError();if(e)throw std::runtime_error(cudaGetErrorString(e));ck(cuStreamSynchronize(g.stream),"position ready");ck(cuCtxSetCurrent(primary),"restore primary");return 0;}CATCH}
extern "C" int gc_capture_begin(int id){TRY{auto&g=groups.at(id);ck(cuCtxSetCurrent(g.ctx),"capture current");ck(cuStreamBeginCapture(g.stream,CU_STREAM_CAPTURE_MODE_THREAD_LOCAL),"begin capture");return 0;}CATCH}
struct Graph{CUgraph graph=nullptr;CUgraphExec exec=nullptr;int group;CUevent a,b;};
extern "C" void*gc_capture_end(int id){try{Graph*p=new Graph;p->group=id;ck(cuStreamEndCapture(groups.at(id).stream,&p->graph),"end capture");ck(cuGraphInstantiate(&p->exec,p->graph,0),"instantiate");ck(cuEventCreate(&p->a,0),"event a");ck(cuEventCreate(&p->b,0),"event b");ck(cuCtxSetCurrent(primary),"restore primary");return p;}catch(std::exception&e){error=e.what();return nullptr;}}
extern "C" int gc_graph_run(void**graphs,int ring,int n,double*out){TRY{for(int i=0;i<n;i++){auto*p=(Graph*)graphs[i%ring];auto&g=groups.at(p->group);ck(cuCtxSetCurrent(g.ctx),"run current");auto t=std::chrono::steady_clock::now();ck(cuEventRecord(p->a,g.stream),"event start");ck(cuGraphLaunch(p->exec,g.stream),"graph launch");ck(cuEventRecord(p->b,g.stream),"event end");ck(cuStreamSynchronize(g.stream),"output ready");out[2*i+1]=std::chrono::duration<double,std::micro>(std::chrono::steady_clock::now()-t).count();float ms;ck(cuEventElapsedTime(&ms,p->a,p->b),"elapsed");out[2*i]=ms*1000;}ck(cuCtxSetCurrent(primary),"restore primary");return 0;}CATCH}
extern "C" int gc_graph_drop(void*ptr){TRY{auto*p=(Graph*)ptr;ck(cuCtxSetCurrent(groups.at(p->group).ctx),"drop current");ck(cuGraphExecDestroy(p->exec),"destroy graph exec");ck(cuGraphDestroy(p->graph),"destroy graph");cuEventDestroy(p->a);cuEventDestroy(p->b);delete p;ck(cuCtxSetCurrent(primary),"restore primary");return 0;}CATCH}

#include "/home/ubuntu/projects/leetgpu-lab/.venv/lib/python3.12/site-packages/nvidia/cublas/include/cublas_v2.h"
void bk(cublasStatus_t x,const char*s){if(x!=CUBLAS_STATUS_SUCCESS)throw std::runtime_error(std::string(s)+":"+std::to_string((int)x));}
extern "C" int gc_primary_stream(){TRY{Resource p;p.ctx=primary;ck(cuCtxSetCurrent(primary),"primary");ck(cuStreamCreate(&p.stream,CU_STREAM_NON_BLOCKING),"additional primary stream");groups.push_back(p);return groups.size()-1;}CATCH}
struct Gemm{cublasHandle_t handle;CUdeviceptr workspace;int group;};
extern "C" void*gc_gemm_create(int group){try{auto*p=new Gemm;p->group=group;ck(cuCtxSetCurrent(groups.at(group).ctx),"gemm current");bk(cublasCreate(&p->handle),"cublasCreate");bk(cublasSetStream(p->handle,(cudaStream_t)groups.at(group).stream),"cublas stream");ck(cuMemAlloc(&p->workspace,64ull<<20),"cublas workspace");bk(cublasSetWorkspace(p->handle,(void*)p->workspace,64ull<<20),"cublas workspace install");bk(cublasSetMathMode(p->handle,CUBLAS_DEFAULT_MATH),"math mode");ck(cuCtxSetCurrent(primary),"restore primary");return p;}catch(std::exception&e){error=e.what();return nullptr;}}
extern "C" int gc_gemm_launch(void*ptr,void*A,void*B,void*Cout,int M,int N,int K){TRY{auto*p=(Gemm*)ptr;const float alpha=1,beta=0;bk(cublasGemmEx(p->handle,CUBLAS_OP_N,CUBLAS_OP_N,N,M,K,&alpha,B,CUDA_R_16F,N,A,CUDA_R_16F,K,&beta,Cout,CUDA_R_32F,N,CUBLAS_COMPUTE_32F,CUBLAS_GEMM_DEFAULT_TENSOR_OP),"cublasGemmEx");return 0;}CATCH}
extern "C" int gc_gemm_drop(void*ptr){TRY{auto*p=(Gemm*)ptr;ck(cuCtxSetCurrent(groups.at(p->group).ctx),"gemm drop current");bk(cublasDestroy(p->handle),"cublas destroy");ck(cuMemFree(p->workspace),"workspace free");delete p;ck(cuCtxSetCurrent(primary),"restore primary");return 0;}CATCH}
struct Mixed{CUevent begin,fgend,bgend,end;int serial;};
extern "C" void*gc_mixed_create(int serial){try{auto*p=new Mixed;p->serial=serial;ck(cuCtxSetCurrent(primary),"mixed primary");for(auto*x:{&p->begin,&p->fgend,&p->bgend,&p->end})ck(cuEventCreate(x,0),"mixed event");return p;}catch(std::exception&e){error=e.what();return nullptr;}}
extern "C" int gc_mixed_run(void*ptr,void**fgs,void**bgs,int ring,int n,double*out){TRY{auto*p=(Mixed*)ptr;
 for(int i=0;i<n;i++){Graph*f=(Graph*)fgs[i%ring];Graph*b=(Graph*)bgs[i%ring];auto&fg=groups.at(f->group);auto&bg=groups.at(b->group);auto&parent=groups.at(0);
  ck(cuCtxSetCurrent(primary),"mixed primary");auto t=std::chrono::steady_clock::now();ck(cuEventRecord(p->begin,parent.stream),"mixed start");
  auto issue=[&](Graph*q,Resource&g,CUevent end,CUevent wait){ck(cuCtxSetCurrent(g.ctx),"mixed context");ck(cuStreamWaitEvent(g.stream,wait,0),"mixed start dependency");ck(cuGraphLaunch(q->exec,g.stream),"mixed graph launch");ck(cuEventRecord(end,g.stream),"chain end");};
  if(p->serial==2){issue(b,bg,p->bgend,p->begin);issue(f,fg,p->fgend,p->bgend);}
  else{issue(f,fg,p->fgend,p->begin);issue(b,bg,p->bgend,p->serial==1?p->fgend:p->begin);}
  ck(cuCtxSetCurrent(primary),"join primary");ck(cuStreamWaitEvent(parent.stream,p->fgend,0),"join fg");ck(cuStreamWaitEvent(parent.stream,p->bgend,0),"join bg");ck(cuEventRecord(p->end,parent.stream),"mixed end");ck(cuStreamSynchronize(parent.stream),"both outputs ready");out[4*i+3]=std::chrono::duration<double,std::micro>(std::chrono::steady_clock::now()-t).count();
  float total,ft,bt;ck(cuEventElapsedTime(&total,p->begin,p->end),"mixed total elapsed");ck(cuEventElapsedTime(&ft,p->begin,p->fgend),"fg completion elapsed");ck(cuEventElapsedTime(&bt,p->begin,p->bgend),"bg completion elapsed");out[4*i]=total*1000;out[4*i+1]=ft*1000;out[4*i+2]=bt*1000;
 }return 0;}CATCH}
extern "C" int gc_mixed_drop(void*ptr){TRY{auto*p=(Mixed*)ptr;cuEventDestroy(p->begin);cuEventDestroy(p->fgend);cuEventDestroy(p->bgend);cuEventDestroy(p->end);delete p;return 0;}CATCH}
