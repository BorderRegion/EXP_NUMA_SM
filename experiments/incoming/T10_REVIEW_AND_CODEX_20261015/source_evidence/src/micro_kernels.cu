#include <cuda_runtime.h>
#include <stdint.h>
struct Task{int family,units;};
__device__ __forceinline__ uint32_t smid(){uint32_t s;asm volatile("mov.u32 %0, %%smid;":"=r"(s));return s;}
__device__ __forceinline__ uint32_t step(uint32_t x,uint32_t j,uint32_t id){return x*1664525u+1013904223u+(j^id);}
// Each logical task is a complete CTA. The numerical body is identical in native
// and persistent table modes; each iteration resets shared state and ends at a barrier.
extern "C" __global__ void micro(const uint32_t* input,uint32_t* output,const Task* meta,const int* table,int count,int stride,int cache_n,int native_mode,int diagnose,uint32_t* diag){
 extern __shared__ uint32_t sh[];
 for(int q=blockIdx.x;q<count;q+=gridDim.x){
  int task=table?table[q]:q;int lane=threadIdx.x;Task m=meta[task];uint32_t id=task*blockDim.x+lane;
  if(diagnose&&lane==0){atomicAdd(diag+task*4,1);diag[task*4+1]=smid();diag[task*4+3]=blockIdx.x;}
  if(m.family==0){uint32_t a=input[id%cache_n],b=a^0x9e3779b9u,c=a+0x1234567u,d=a^id;
   for(int j=0;j<m.units;j++){a=step(a,j,id);b=step(b,j,id+1);c=step(c,j,id+2);d=step(d,j,id+3);}output[(size_t)task*stride+lane]=a^b^c^d;
  }else if(m.family==1){
   uint32_t sum=0;for(int j=0;j<m.units;j++){uint32_t v=input[(task*blockDim.x+lane+j*blockDim.x)%cache_n];sh[j*blockDim.x+lane]=v*3u+uint32_t(j);}
   __syncthreads();for(int j=0;j<m.units;j++)sum+=sh[j*blockDim.x+((lane+j)%blockDim.x)];output[(size_t)task*stride+lane]=sum;
  }else if(m.family==2){
   uint32_t acc=0;for(int j=0;j<m.units;j++){unsigned off=(task*1024+lane+(j%8)*blockDim.x)%cache_n;uint32_t v;asm volatile("ld.global.cg.u32 %0, [%1];":"=r"(v):"l"(input+off):"memory");acc=step(acc,v,j);}output[(size_t)task*stride+lane]=acc;
  }else{
   for(int j=lane;j<stride;j+=blockDim.x){size_t off=(size_t)task*stride+j;output[off]=input[off]*3u+uint32_t(off);}
  }
  __syncthreads();if(diagnose&&lane==0)diag[task*4+2]=smid();
  __syncthreads();if(native_mode)break;
 }
}
extern "C" __global__ void digest(const uint32_t* out,unsigned long long* result,size_t n){
 unsigned long long x=0;for(size_t i=threadIdx.x;i<n;i+=blockDim.x)x+=(unsigned long long)out[i]*(i+1);
 __shared__ unsigned long long s[256];s[threadIdx.x]=x;__syncthreads();for(int k=blockDim.x/2;k;k/=2){if(threadIdx.x<k)s[threadIdx.x]+=s[threadIdx.x+k];__syncthreads();}if(!threadIdx.x)*result=s[0];
}
