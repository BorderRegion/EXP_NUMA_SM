#include <cuda_runtime.h>
#include "probe_types.hpp"
__device__ __forceinline__ unsigned smid(){unsigned r;asm volatile("mov.u32 %0, %%smid;":"=r"(r));return r;}
__device__ __forceinline__ unsigned load(const unsigned*p,int cg){unsigned x;if(cg)asm volatile("ld.global.cg.u32 %0,[%1];":"=r"(x):"l"(p):"memory");else asm volatile("ld.global.u32 %0,[%1];":"=r"(x):"l"(p):"memory");return x;}
__device__ __forceinline__ unsigned phys(unsigned region,unsigned offset,unsigned window){return ((offset/window)*64+region)*window+offset%window;}
// Only the diagnostic probe reads a task permutation. No application method is
// implemented here. Each full consumer accesses the complete per-region set.
extern "C" __global__ void probe(const unsigned* data,const unsigned* perm,const unsigned* starts,ProbeRecord*out,unsigned region_words,unsigned window,unsigned task_base,int mode,int cg,int repeats){
 __shared__ unsigned long long sums[128],begin;
 __shared__ unsigned sm;
 for(unsigned pos=task_base+blockIdx.x;pos<512;pos+=gridDim.x){
 unsigned q=perm[pos],region=q/8;
 if(mode>=4){
  if(threadIdx.x==0){unsigned idx=starts[q],first=idx;unsigned long long sum=0;unsigned sb=smid();unsigned long long t=clock64();
   #pragma unroll 1
   for(int i=0;i<256;i++){if(mode==4)idx=load(data+idx,cg);else asm volatile("mad.lo.u32 %0,%0,1664525,1013904223;":"+r"(idx));sum+=idx;}
   unsigned long long elapsed=clock64()-t;out[pos]={elapsed,sum,sb,smid(),region,pos,first,idx,256,0};
  }continue;
 }
 if(!threadIdx.x){sm=smid();begin=clock64();}__syncthreads();
 unsigned long long sum=0;
 for(int rep=0;rep<repeats;rep++)for(unsigned j=threadIdx.x;j<region_words;j+=blockDim.x){
  unsigned k=(mode&1)?((j*405u+region*17u+3u)&(region_words-1)):j;
  sum+=load(data+phys(region,k,window),cg);
 }
 sums[threadIdx.x]=sum;__syncthreads();
 for(int d=64;d;d/=2){if(threadIdx.x<d)sums[threadIdx.x]+=sums[threadIdx.x+d];__syncthreads();}
 if(!threadIdx.x)out[pos]={clock64()-begin,sums[0],sm,smid(),region,pos,0,0,region_words*unsigned(repeats),0};
 __syncthreads();
 }
}
extern "C" __global__ void sweep(const unsigned* data,unsigned words,unsigned long long*out){
 unsigned long long sum=0;for(unsigned i=blockIdx.x*blockDim.x+threadIdx.x;i<words;i+=gridDim.x*blockDim.x)sum+=load(data+i,1);
 __shared__ unsigned long long s[128];s[threadIdx.x]=sum;__syncthreads();for(int d=64;d;d/=2){if(threadIdx.x<d)s[threadIdx.x]+=s[threadIdx.x+d];__syncthreads();}if(!threadIdx.x)out[blockIdx.x]=s[0];
}
// Finite, table-free arithmetic placement diagnostic. A parity mask encodes
// equal classes. It is supplied once per launch, never looked up per task/page.
// No hardware home is assumed. Four cell probes and matched/reversed whole-pool
// executions are evidence about a calibration, not a declared NUMA method.
__device__ __forceinline__ unsigned slot(unsigned j,unsigned d,unsigned mask,unsigned bias){
 unsigned p=__ffs(mask)-1,u=(j&((1u<<p)-1))|((j>>p)<<(p+1));
 return u|(((__popc(u&mask)&1)^bias^d)<<p);
}
extern "C" __global__ void parity_consume(const unsigned*data,unsigned long long*out,ProbeRecord*diag,unsigned region_words,unsigned window,unsigned mask,unsigned bias,unsigned data_class,unsigned logical_xor,int cg,int repeats){
 unsigned j=blockIdx.x,region=slot(j,data_class,mask,bias),logical_region=region^logical_xor;
 __shared__ unsigned long long sums[128],begin;__shared__ unsigned sm;
 if(!threadIdx.x){begin=clock64();sm=smid();}__syncthreads();unsigned long long sum=0;
 for(int r=0;r<repeats;r++)for(unsigned k=threadIdx.x;k<region_words;k+=128)sum+=load(data+phys(region,k,window),cg);
 sums[threadIdx.x]=sum;__syncthreads();for(int d=64;d;d/=2){if(threadIdx.x<d)sums[threadIdx.x]+=sums[threadIdx.x+d];__syncthreads();}
 if(!threadIdx.x){out[logical_region]=sums[0];if(diag)diag[j]={clock64()-begin,sums[0],sm,smid(),region,j,0,0,region_words*unsigned(repeats),0};}
}
