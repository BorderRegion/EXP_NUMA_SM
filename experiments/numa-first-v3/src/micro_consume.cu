#include <cuda_runtime.h>
#include "probe_types.hpp"
__device__ __forceinline__ unsigned smid(){unsigned r;asm volatile("mov.u32 %0, %%smid;":"=r"(r));return r;}
__device__ __forceinline__ unsigned slot(unsigned j,unsigned d,unsigned mask,unsigned bias){unsigned p=__ffs(mask)-1,u=(j&((1u<<p)-1))|((j>>p)<<(p+1));return u|(((__popc(u&mask)&1)^bias^d)<<p);}
extern "C" __global__ void micro_consume(const unsigned*data,unsigned long long*out,ProbeRecord*diag,unsigned rw,unsigned mask,unsigned bias,unsigned data_class,int colored,int repeats){
 unsigned j=blockIdx.x,r=mask?slot(j,data_class,mask,bias):j,logical=colored?data_class*32+j:r;
 __shared__ unsigned long long sums[128],begin;__shared__ unsigned sm;
 if(!threadIdx.x){sm=smid();begin=clock64();}__syncthreads();unsigned long long sum=0;
 for(int rep=0;rep<repeats;rep++)for(unsigned k=threadIdx.x;k<rw;k+=128){unsigned idx=(((k>>10)*64+r)<<10)+(k&1023);unsigned v;asm volatile("ld.global.cg.u32 %0,[%1];":"=r"(v):"l"(data+idx):"memory");sum+=v;}
 sums[threadIdx.x]=sum;__syncthreads();for(int d=64;d;d/=2){if(threadIdx.x<d)sums[threadIdx.x]+=sums[threadIdx.x+d];__syncthreads();}
 if(!threadIdx.x){out[logical]=sums[0];diag[logical]={clock64()-begin,sums[0],sm,smid(),r,logical,0,0,rw*unsigned(repeats),0};}
}
