#include "probe.cu"
static thread_local const char *message="";
extern "C" const char *probe_error(){return message;}
extern "C" int probe_launch(void *flags, void *records, const int *params,
                            void *mapping, unsigned long long stream){
    Plan p;static_assert(sizeof(p)==9*sizeof(int));
    const char *src=(const char*)params;char *dst=(char*)&p;
    for(unsigned i=0;i<sizeof(p);++i)dst[i]=src[i];
    auto e=cudaFuncSetAttribute(probe,cudaFuncAttributeMaxDynamicSharedMemorySize,48*1024);
    int active=0;
    if(e==cudaSuccess)e=cudaOccupancyMaxActiveBlocksPerMultiprocessor(&active,probe,64,48*1024);
    if(e==cudaSuccess&&active!=1)e=cudaErrorInvalidConfiguration;
    const unsigned *chain=nullptr,*starts=nullptr;
    void *args[]={&flags,&chain,&starts,&records,&p,&mapping};
    if(e==cudaSuccess)e=cudaLaunchCooperativeKernel((void*)probe,56,64,args,48*1024,(cudaStream_t)stream);
    if(e!=cudaSuccess){message=cudaGetErrorString(e);return -1;}return 0;
}
