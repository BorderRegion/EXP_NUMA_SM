// Retarget the same graph executable/stream/events: schedule, flags and page.
// Formal GPU operator binary and graph topology remain identical.
#include <cuda.h>
#include <chrono>
#include <cstring>
#include <stdexcept>
#include <string>
#include <vector>
#include <cstdint>
#include <cstdio>
static thread_local std::string error;
static void ck(CUresult x,const char *s){if(x){const char *p=nullptr;cuGetErrorString(x,&p);throw std::runtime_error(std::string(s)+":"+(p?p:"unknown"));}}
struct Shared {
 CUgraph body=nullptr,outer=nullptr;CUgraphNode child=nullptr;
 CUgraphExec exec=nullptr;CUstream stream=nullptr;CUevent begin=nullptr,end=nullptr;
 std::vector<CUgraphNode> kernels;std::string identity;
 Shared(void *original){
  ck(cuGraphClone(&body,(CUgraph)original),"clone");
  size_t n=0;ck(cuGraphGetNodes(body,nullptr,&n),"count");std::vector<CUgraphNode> nodes(n);ck(cuGraphGetNodes(body,nodes.data(),&n),"nodes");
  for(auto node:nodes){CUgraphNodeType t;ck(cuGraphNodeGetType(node,&t),"type");if(t!=CU_GRAPH_NODE_TYPE_KERNEL)throw std::runtime_error("unexpected non-kernel node");CUDA_KERNEL_NODE_PARAMS p{};ck(cuGraphKernelNodeGetParams(node,&p),"params");const char *name=nullptr;if(p.func)ck(cuFuncGetName(&name,p.func),"name");else if(p.kern)ck(cuKernelGetName(&name,p.kern),"kernel name");else throw std::runtime_error("missing function");if(std::string(name).find("paired")!=std::string::npos){if(!p.kernelParams||p.extra)throw std::runtime_error("unsupported argument encoding");kernels.push_back(node);}}
  if(kernels.size()!=1&&kernels.size()!=32)throw std::runtime_error("unexpected paired count");
  ck(cuStreamCreate(&stream,CU_STREAM_NON_BLOCKING),"stream");ck(cuEventCreate(&begin,0),"begin");ck(cuEventCreate(&end,0),"end");
  ck(cuGraphCreate(&outer,0),"outer");CUgraphNode a,c;
  ck(cuGraphAddEventRecordNode(&a,outer,nullptr,0,begin),"begin node");
  ck(cuGraphAddChildGraphNode(&child,outer,&a,1,body),"child");
  ck(cuGraphAddEventRecordNode(&c,outer,&child,1,end),"end node");
  ck(cuGraphInstantiate(&exec,outer,0),"instantiate");
  char buf[512];std::snprintf(buf,sizeof(buf),"{\"body\":%llu,\"outer\":%llu,\"exec\":%llu,\"stream\":%llu,\"begin\":%llu,\"end\":%llu,\"paired_nodes\":%zu}",(unsigned long long)(uintptr_t)body,(unsigned long long)(uintptr_t)outer,(unsigned long long)(uintptr_t)exec,(unsigned long long)(uintptr_t)stream,(unsigned long long)(uintptr_t)begin,(unsigned long long)(uintptr_t)end,kernels.size());identity=buf;
 }
 ~Shared(){if(exec)cuGraphExecDestroy(exec);if(outer)cuGraphDestroy(outer);if(body)cuGraphDestroy(body);if(begin)cuEventDestroy(begin);if(end)cuEventDestroy(end);if(stream)cuStreamDestroy(stream);}
 int set(const int *schedule,unsigned long long newflags,int newpage){
  int copy[56];std::memcpy(copy,schedule,sizeof(copy));
  for(auto node:kernels){
   CUDA_KERNEL_NODE_PARAMS p{};ck(cuGraphKernelNodeGetParams(node,&p),"old params");
   uint64_t x,y,flags,trace;int page;
   std::memcpy(&x,p.kernelParams[0],8);std::memcpy(&y,p.kernelParams[1],8);std::memcpy(&flags,p.kernelParams[2],8);std::memcpy(&page,p.kernelParams[4],4);std::memcpy(&trace,p.kernelParams[5],8);
   flags=newflags;page=newpage;
   void *args[]={&x,&y,&flags,&copy,&page,&trace};p.kernelParams=args;p.extra=nullptr;
   ck(cuGraphKernelNodeSetParams(node,&p),"set params");
   CUDA_KERNEL_NODE_PARAMS q{};ck(cuGraphKernelNodeGetParams(node,&q),"verify params");
   if(std::memcmp(q.kernelParams[3],copy,sizeof(copy))||std::memcmp(q.kernelParams[2],&flags,8)||std::memcmp(q.kernelParams[4],&page,4))throw std::runtime_error("schedule readback mismatch");
  }
  ck(cuGraphExecChildGraphNodeSetParams(exec,child,body),"update executable child");return kernels.size();
 }
 void run(int n,double *out){for(int i=0;i<n;i++){auto t=std::chrono::steady_clock::now();ck(cuGraphLaunch(exec,stream),"launch");ck(cuStreamSynchronize(stream),"ready");out[2*i+1]=std::chrono::duration<double,std::micro>(std::chrono::steady_clock::now()-t).count();float ms=0;ck(cuEventElapsedTime(&ms,begin,end),"elapsed");out[2*i]=ms*1000;}}
};
extern "C" const char *sg_error(){return error.c_str();}
extern "C" void *sg_create(void *body){try{return new Shared(body);}catch(std::exception&e){error=e.what();return nullptr;}}
extern "C" const char *sg_identity(Shared *p){return p->identity.c_str();}
extern "C" int sg_set(Shared *p,const int *s,unsigned long long flags,int page){try{return p->set(s,flags,page);}catch(std::exception&e){error=e.what();return -1;}}
extern "C" int sg_run(Shared *p,int n,double *v){try{p->run(n,v);return 0;}catch(std::exception&e){error=e.what();return -1;}}
// Batched host-side sampler. First column is update wall us; subsequent
// columns alternate GPU event and host replay time. No new device code.
extern "C" int sg_scan(Shared *p,const int *maps,const unsigned long long *flags,
 const int *pages,const int *ids,int n,int replays,double *out){
 try{
  if(n<1||replays<1)throw std::runtime_error("empty scan");
  for(int i=0;i<n;i++){
   int k=ids[i];if(k<0||k>=132)throw std::runtime_error("choice out of bounds");
   auto t=std::chrono::steady_clock::now();p->set(maps+k*56,flags[k],pages[k]);
   double *row=out+i*(1+2*replays);
   row[0]=std::chrono::duration<double,std::micro>(std::chrono::steady_clock::now()-t).count();
   p->run(replays,row+1);
  }
  return 0;
 }catch(std::exception&e){error=e.what();return -1;}
}
extern "C" void sg_drop(Shared *p){delete p;}
