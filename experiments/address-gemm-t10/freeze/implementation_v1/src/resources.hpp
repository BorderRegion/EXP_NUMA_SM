#pragma once
#include "driver_backend.hpp"
// Primary construction performs no resource enumeration or Green creation.
struct Resources {
 CUdevice dev; CUcontext primary; std::vector<Group> groups; std::vector<CUdevResource> resources;
 double driver_init_ms=0,enumeration_ms=0,green_create_ms=0;
 Resources(){auto a=Clock::now();ck(cuInit(0),"init");ck(cuDeviceGet(&dev,0),"device");ck(cuDevicePrimaryCtxRetain(&primary,dev),"retain");ck(cuCtxSetCurrent(primary),"primary");driver_init_ms=ms(a,Clock::now());}
 void inventory(){if(!resources.empty())return;auto a=Clock::now();CUdevResource all{},rem{};ck(cuDeviceGetDevResource(dev,&all,CU_DEV_RESOURCE_TYPE_SM),"resources");unsigned n=0;ck(cuDevSmResourceSplitByCount(nullptr,&n,&all,nullptr,0,2),"split count");if(n!=28)throw std::runtime_error("T10 56 SM contract");resources.resize(n);ck(cuDevSmResourceSplitByCount(resources.data(),&n,&all,&rem,0,2),"split resources");enumeration_ms=ms(a,Clock::now());}
 int merge(const std::vector<int>&ids){inventory();auto a=Clock::now();std::vector<CUdevResource> rs;for(int id:ids)rs.push_back(resources.at(id));Group g;CUdevResourceDesc d;ck(cuDevResourceGenerateDesc(&d,rs.data(),rs.size()),"merged descriptor");ck(cuGreenCtxCreate(&g.green,d,dev,CU_GREEN_CTX_DEFAULT_STREAM),"green create");ck(cuCtxFromGreenCtx(&g.ctx,g.green),"green convert");g.sms=ids.size()*2;ck(cuCtxSetCurrent(g.ctx),"green current");ck(cuGreenCtxStreamCreate(&g.stream,g.green,CU_STREAM_NON_BLOCKING,0),"green stream");groups.push_back(g);green_create_ms+=ms(a,Clock::now());return groups.size()-1;}
 void current(int g){ck(cuCtxSetCurrent(groups.at(g).ctx),"current group");}
 ~Resources(){for(auto&g:groups){cuCtxSetCurrent(g.ctx);cuStreamDestroy(g.stream);cuCtxSetCurrent(primary);cuGreenCtxDestroy(g.green);}cuDevicePrimaryCtxRelease(dev);}
};
