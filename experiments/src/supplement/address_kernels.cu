#include <cuda_runtime.h>
#include "address_common.hpp"
__device__ __forceinline__ unsigned observed_sm(){unsigned x;asm volatile("mov.u32 %0, %%smid;":"=r"(x));return x;}
__device__ __forceinline__ unsigned read_word(const unsigned*p,int cg){unsigned v;if(cg)asm volatile("ld.global.cg.u32 %0,[%1];":"=r"(v):"l"(p):"memory");else asm volatile("ld.global.u32 %0,[%1];":"=r"(v):"l"(p):"memory");return v;}
__device__ __forceinline__ unsigned physical(unsigned r,unsigned offset,unsigned regions,unsigned window){return ((offset/window)*regions+r)*window+offset%window;}
extern "C" __global__ void prepare_input(const unsigned*data,unsigned n,unsigned long long*out){unsigned long long s=0;for(unsigned i=blockIdx.x*blockDim.x+threadIdx.x;i<n;i+=gridDim.x*blockDim.x)s+=data[i];__shared__ unsigned long long a[128];a[threadIdx.x]=s;__syncthreads();for(int d=64;d;d/=2){if(threadIdx.x<d)a[threadIdx.x]+=a[threadIdx.x+d];__syncthreads();}if(!threadIdx.x)out[blockIdx.x]=a[0];}
extern "C" __global__ void address_probe(const unsigned*data,const unsigned*task_permutation,ProbeState*states,ProbeRecord*records,unsigned regions,unsigned window,unsigned segment,unsigned segment_words,int cg,int throughput){
 unsigned q=task_permutation[blockIdx.x],r=q/8;ProbeRecord*rec=records+(size_t)segment*gridDim.x+q;
 if(!throughput){if(threadIdx.x==0){unsigned idx=states[q].index,first=idx,s=0;unsigned sm=observed_sm();unsigned long long t=clock64();for(unsigned i=0;i<segment_words;i++){idx=read_word(data+idx,cg);s+=idx;}unsigned long long elapsed=clock64()-t;states[q].index=idx;states[q].sum+=s;*rec={elapsed,sm,observed_sm(),first,idx,s,segment_words};}return;}
 __shared__ unsigned sums[128];__shared__ unsigned long long begin;__shared__ unsigned sm;
 if(!threadIdx.x){sm=observed_sm();begin=clock64();}__syncthreads();unsigned s=0,offset=segment*segment_words;
 for(unsigned j=threadIdx.x;j<segment_words;j+=blockDim.x)s+=read_word(data+physical(r,offset+j,regions,window),cg);
 sums[threadIdx.x]=s;__syncthreads();for(int d=64;d;d/=2){if(threadIdx.x<d)sums[threadIdx.x]+=sums[threadIdx.x+d];__syncthreads();}
 if(!threadIdx.x){unsigned long long elapsed=clock64()-begin;states[q].sum+=sums[0];*rec={elapsed,sm,observed_sm(),offset,offset+segment_words,sums[0],segment_words};}
}
// One complete 4KiB task, repeated a fixed useful eight times. Diagnostic
// local clocks/SM/visits are disabled in all formal timed epochs.
extern "C" __global__ void address_work(const unsigned*data,unsigned long long*out,const int*table,int count,int irregular,int repeats,TaskRecord*diag){
 __shared__ unsigned long long sum[128],begin;__shared__ unsigned sm;
 for(int q=blockIdx.x;q<count;q+=gridDim.x){int task=table?table[q]:q;if(diag&&!threadIdx.x){begin=clock64();sm=observed_sm();}__syncthreads();unsigned long long x=0;
  for(int rep=0;rep<repeats;rep++)for(int j=threadIdx.x;j<1024;j+=blockDim.x){unsigned k=irregular?((unsigned(j)*405+unsigned(task)*17+3)&1023):unsigned(j);unsigned off=unsigned(task)*1024+k;unsigned v=read_word(data+off,0);x+=(unsigned long long)v*(off+1ull);}
  sum[threadIdx.x]=x;__syncthreads();for(int d=64;d;d/=2){if(threadIdx.x<d)sum[threadIdx.x]+=sum[threadIdx.x+d];__syncthreads();}
  if(!threadIdx.x){out[task]=sum[0];if(diag){diag[task].ticks=clock64()-begin;diag[task].sm_begin=sm;diag[task].sm_end=observed_sm();atomicAdd(&diag[task].visits,1u);}}__syncthreads();
 }
}
