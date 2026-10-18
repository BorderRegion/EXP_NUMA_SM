#pragma once
#include <cuda.h>
#include <vector>
#include <string>
#include <stdexcept>
#include <chrono>
inline void ck(CUresult e,const char* s){if(e){const char* n="unknown";cuGetErrorName(e,&n);throw std::runtime_error(std::string(s)+": "+n);}}
using Clock=std::chrono::steady_clock;
inline double ms(Clock::time_point a,Clock::time_point b){return std::chrono::duration<double,std::milli>(b-a).count();}
struct Group{CUgreenCtx green=nullptr;CUcontext ctx=nullptr;CUstream stream=nullptr;CUevent start=nullptr,end=nullptr;int sms=0;};
struct Backend{
 CUdevice dev;CUcontext primary;int sms;std::vector<Group> groups;
 Backend(int layout){
  ck(cuInit(0),"cuInit");ck(cuDeviceGet(&dev,0),"device");ck(cuDevicePrimaryCtxRetain(&primary,dev),"retain");ck(cuCtxSetCurrent(primary),"primary");
  ck(cuDeviceGetAttribute(&sms,CU_DEVICE_ATTRIBUTE_MULTIPROCESSOR_COUNT,dev),"sm count");
  if(layout<0){Group g;g.ctx=primary;g.sms=sms;groups.push_back(g);}else{
   CUdevResource all{};ck(cuDeviceGetDevResource(dev,&all,CU_DEV_RESOURCE_TYPE_SM),"all resources");
   std::vector<CUdevResource> rs;
   if(layout==0)rs.push_back(all);else{CUdevResource a{},rem{};unsigned n=1;
    ck(cuDevSmResourceSplitByCount(&a,&n,&all,&rem,layout==3?CU_DEV_SM_RESOURCE_SPLIT_IGNORE_SM_COSCHEDULING:0,layout==2?sms/3:sms/2),"split");
    if(n)rs.push_back(a);if(rem.type==CU_DEV_RESOURCE_TYPE_SM&&rem.sm.smCount)rs.push_back(rem);
   }
   int sum=0;for(auto&r:rs){Group g;CUdevResourceDesc desc;ck(cuDevResourceGenerateDesc(&desc,&r,1),"descriptor");ck(cuGreenCtxCreate(&g.green,desc,dev,CU_GREEN_CTX_DEFAULT_STREAM),"green create");ck(cuCtxFromGreenCtx(&g.ctx,g.green),"convert");g.sms=r.sm.smCount;sum+=g.sms;groups.push_back(g);}
   if(sum!=sms)throw std::runtime_error("dropped resources");
  }
  for(auto&g:groups){ck(cuCtxSetCurrent(g.ctx),"set group");if(g.green)ck(cuGreenCtxStreamCreate(&g.stream,g.green,CU_STREAM_NON_BLOCKING,0),"green stream");else ck(cuStreamCreate(&g.stream,CU_STREAM_NON_BLOCKING),"stream");ck(cuEventCreate(&g.start,CU_EVENT_DEFAULT),"start event");ck(cuEventCreate(&g.end,CU_EVENT_DEFAULT),"end event");}
  ck(cuCtxSetCurrent(primary),"restore primary");
 }
 void current(int g){ck(cuCtxSetCurrent(groups.at(g).ctx),"current");}
 void join(){for(auto&g:groups){ck(cuCtxSetCurrent(g.ctx),"join context");ck(cuStreamSynchronize(g.stream),"join");}ck(cuCtxSetCurrent(primary),"restore");}
 ~Backend(){for(auto&g:groups){cuCtxSetCurrent(g.ctx);cuEventDestroy(g.start);cuEventDestroy(g.end);cuStreamDestroy(g.stream);cuCtxSetCurrent(primary);if(g.green)cuGreenCtxDestroy(g.green);}cuDevicePrimaryCtxRelease(dev);}
};
struct Buffer{CUdeviceptr p=0;size_t bytes=0;Buffer(){}explicit Buffer(size_t n):bytes(n){ck(cuMemAlloc(&p,n),"allocate");}void upload(const void*x){ck(cuMemcpyHtoD(p,x,bytes),"upload");}void download(void*x){ck(cuMemcpyDtoH(x,p,bytes),"download");}~Buffer(){if(p)cuMemFree(p);}Buffer(const Buffer&)=delete;Buffer&operator=(const Buffer&)=delete;};
