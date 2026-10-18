#include <cuda.h>
#include <iostream>
#include <stdexcept>
#include <vector>
static void ck(CUresult e,const char* label){if(e){const char* s;cuGetErrorName(e,&s);throw std::runtime_error(std::string(label)+": "+s);}}
int main(){try{
  ck(cuInit(0),"init");CUdevice d;ck(cuDeviceGet(&d,0),"device");
  CUcontext primary;ck(cuDevicePrimaryCtxRetain(&primary,d),"retain");ck(cuCtxSetCurrent(primary),"current");
  CUdevResource all{};ck(cuDeviceGetDevResource(d,&all,CU_DEV_RESOURCE_TYPE_SM),"resource");
  std::cout<<"{\"total_sm\":"<<all.sm.smCount<<",\"layouts\":[";
  for(int l=0;l<4;l++){
    if(l)std::cout<<',';
    std::vector<CUdevResource> rs;unsigned request=l==2?all.sm.smCount/3:all.sm.smCount/2;
    if(!l)rs.push_back(all);else{
      CUdevResource r{},rem{};unsigned n=1;CUresult e=cuDevSmResourceSplitByCount(&r,&n,&all,&rem,l==3?CU_DEV_SM_RESOURCE_SPLIT_IGNORE_SM_COSCHEDULING:0,request);
      if(e){const char* s;cuGetErrorName(e,&s);std::cout<<"{\"layout\":\"G"<<l<<"\",\"error\":\""<<s<<"\"}";continue;}
      if(n)rs.push_back(r);if(rem.type==CU_DEV_RESOURCE_TYPE_SM&&rem.sm.smCount)rs.push_back(rem);
    }
    std::cout<<"{\"layout\":\"G"<<l<<"\",\"requested\":"<<(l?request:all.sm.smCount)<<",\"groups\":[";
    for(size_t g=0;g<rs.size();g++){
      CUdevResourceDesc desc;ck(cuDevResourceGenerateDesc(&desc,&rs[g],1),"desc");
      CUgreenCtx gc;ck(cuGreenCtxCreate(&gc,desc,d,CU_GREEN_CTX_DEFAULT_STREAM),"create");
      CUcontext ctx;ck(cuCtxFromGreenCtx(&ctx,gc),"convert");ck(cuCtxSetCurrent(ctx),"green current");
      CUstream stream;ck(cuGreenCtxStreamCreate(&stream,gc,CU_STREAM_NON_BLOCKING,0),"stream");
      ck(cuStreamSynchronize(stream),"sync");ck(cuStreamDestroy(stream),"destroy stream");
      CUdevResource observed{};ck(cuGreenCtxGetDevResource(gc,&observed,CU_DEV_RESOURCE_TYPE_SM),"query green");
      if(g)std::cout<<',';std::cout<<observed.sm.smCount;
      ck(cuCtxSetCurrent(primary),"restore");ck(cuGreenCtxDestroy(gc),"destroy");
    }std::cout<<"]}";
  }std::cout<<"],\"kernel_executed\":false}\n";
  cuDevicePrimaryCtxRelease(d);return 0;
}catch(std::exception&e){std::cerr<<e.what()<<'\n';return 2;}}
