// Minimal, finite, diagnostic-only cluster co-occurrence probe.
// Not a scheduler; not a benchmark; no performance numbers or GPC completion claims.
// Compile ONLY with appropriate local CUDA headers/compiler and supported target.
// nvcc -O2 -std=c++17 -arch=sm_120 cluster_probe.cu -o cluster_probe
// ./cluster_probe <cluster_size> <number_of_clusters> <iterations>
#include <cuda_runtime.h>
#include <cooperative_groups.h>
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <string>
namespace cg=cooperative_groups;
#if CUDART_VERSION >= 12000
struct Row { uint32_t block,cluster,rank,sm_begin,sm_end; };
__device__ __forceinline__ uint32_t smid() { uint32_t s;asm volatile("mov.u32 %0, %%smid;":"=r"(s));return s; }
__global__ void observe(Row* rows,uint32_t* values,uint32_t iters,uint32_t k) {
#if __CUDA_ARCH__ >= 900
    const unsigned b=blockIdx.x,t=threadIdx.x,idx=b*blockDim.x+t;
    uint32_t s0=0;if(t==0)s0=smid();
    uint32_t x=idx*747796405u+2891336453u;
    for(uint32_t j=0;j<iters;++j)x=x*1664525u+1013904223u+(j^idx);
    values[idx]=x;
    if(t==0) {
        Row r;r.block=b;r.cluster=b/k;r.rank=cg::this_cluster().block_rank();r.sm_begin=s0;r.sm_end=smid();rows[b]=r;
    }
#endif
}
static void ck(cudaError_t e,const char* w) {if(e!=cudaSuccess)throw std::runtime_error(std::string(w)+": "+cudaGetErrorString(e));}
int main(int argc,char**argv) {
    Row* rows=nullptr;uint32_t* values=nullptr;
    try {
        unsigned k=argc>1?std::stoul(argv[1]):2, nc=argc>2?std::stoul(argv[2]):64, it=argc>3?std::stoul(argv[3]):512;
        if(k<1||k>8||nc<1||nc>256||it<1||it>4096)throw std::runtime_error("bounded argument limits exceeded");
        cudaDeviceProp p{};ck(cudaGetDeviceProperties(&p,0),"properties");
        int yes=0;ck(cudaDeviceGetAttribute(&yes,cudaDevAttrClusterLaunch,0),"cluster attribute");
        if(p.major<9||!yes){std::cerr<<"UNSUPPORTED_CLUSTER\n";return 3;}
        constexpr unsigned threads=128;unsigned nb=k*nc;
        cudaLaunchAttribute attr{};attr.id=cudaLaunchAttributeClusterDimension;
        attr.val.clusterDim.x=k;attr.val.clusterDim.y=1;attr.val.clusterDim.z=1;
        cudaLaunchConfig_t cfg{};cfg.gridDim=dim3(nb,1,1);cfg.blockDim=dim3(threads,1,1);cfg.attrs=&attr;cfg.numAttrs=1;
        int active=0;
        cudaError_t occ=cudaOccupancyMaxActiveClusters(&active,(const void*)observe,&cfg);
        if(occ!=cudaSuccess||active<=0){std::cerr<<"UNSUPPORTED_KERNEL_CLUSTER_CONFIG: "<<cudaGetErrorString(occ)<<"\n";return 3;}
        ck(cudaMalloc(&rows,nb*sizeof(Row)),"allocate rows");ck(cudaMalloc(&values,nb*threads*sizeof(uint32_t)),"allocate values");
        ck(cudaMemset(rows,0xff,nb*sizeof(Row)),"initialize diagnostic rows");
        ck(cudaLaunchKernelEx(&cfg,observe,rows,values,it,k),"cluster launch");
        ck(cudaDeviceSynchronize(),"completion");
        Row* hr=new Row[nb];uint32_t* hv=new uint32_t[nb*threads];
        ck(cudaMemcpy(hr,rows,nb*sizeof(Row),cudaMemcpyDeviceToHost),"row readback");
        ck(cudaMemcpy(hv,values,nb*threads*sizeof(uint32_t),cudaMemcpyDeviceToHost),"value readback");
        for(unsigned idx=0;idx<nb*threads;++idx){uint32_t x=idx*747796405u+2891336453u;for(uint32_t j=0;j<it;++j)x=x*1664525u+1013904223u+(j^idx);if(x!=hv[idx])throw std::runtime_error("uint output mismatch");}
        std::cout<<"block_id,cluster_id,rank,sm_begin,sm_end,cluster_size,static_active_cluster_capacity\n";
        for(unsigned b=0;b<nb;++b)std::cout<<hr[b].block<<','<<hr[b].cluster<<','<<hr[b].rank<<','<<hr[b].sm_begin<<','<<hr[b].sm_end<<','<<k<<','<<active<<'\n';
        delete[] hr;delete[] hv;ck(cudaFree(rows),"free rows");rows=nullptr;ck(cudaFree(values),"free values");values=nullptr;
        return 0;
    }catch(const std::exception&e){std::cerr<<e.what()<<'\n';if(rows)cudaFree(rows);if(values)cudaFree(values);return 2;}
}
#else
int main(){std::cerr<<"LOCAL_HEADERS_TOO_OLD_FOR_THIS_STARTER\n";return 3;}
#endif
