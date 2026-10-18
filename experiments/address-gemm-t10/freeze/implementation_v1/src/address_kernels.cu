#include <cuda_runtime.h>
#include <cooperative_groups.h>
namespace cg=cooperative_groups;
constexpr int NSM=56, CHUNK=2048;
__device__ __forceinline__ unsigned smid(){unsigned x;asm volatile("mov.u32 %0, %%smid;":"=r"(x));return x;}
__device__ __forceinline__ unsigned long long timer(){unsigned long long x;asm volatile("mov.u64 %0, %%globaltimer;":"=l"(x));return x;}
__device__ __forceinline__ float4 load_cg(const float*p){float4 v;asm volatile("ld.global.cg.v4.f32 {%0,%1,%2,%3}, [%4];":"=f"(v.x),"=f"(v.y),"=f"(v.z),"=f"(v.w):"l"(p):"memory");return v;}
// Same ordered FP32 split reduction for every new scheduling policy.
__device__ void reduce_chunk(const float*w,float*d,const float*c,int count,int splits,int task,float alpha,float beta){
 for(int i=task*CHUNK+threadIdx.x*4;i<min((task+1)*CHUNK,count);i+=blockDim.x*4){
  float4 sum=make_float4(0,0,0,0);
  for(int s=0;s<splits;s++){float4 x=load_cg(w+(long long)s*count+i);sum.x+=x.x;sum.y+=x.y;sum.z+=x.z;sum.w+=x.w;}
  float4 cc=make_float4(0,0,0,0);if(beta!=0)cc=*((const float4*)(c+i));
  *((float4*)(d+i))=make_float4(alpha*sum.x+beta*cc.x,alpha*sum.y+beta*cc.y,alpha*sum.z+beta*cc.z,alpha*sum.w+beta*cc.w);
 }
}
extern "C" __global__ void address_reduce(const float*w,float*d,const float*c,int count,int splits,const int*map,int waves,float alpha,float beta){
 unsigned sm=smid();cg::this_grid().sync();
 for(int wave=0;wave<waves;wave++){int task=map[sm*waves+wave];if(task>=0)reduce_chunk(w,d,c,count,splits,task,alpha,beta);}
}
extern "C" __global__ void linear_reduce(const float*w,float*d,const float*c,int count,int splits,const int*map,int waves,float alpha,float beta){reduce_chunk(w,d,c,count,splits,blockIdx.x,alpha,beta);}
extern "C" __global__ void address_probe(const float*w,float*d,const float*c,int count,int splits,int target,const int*order,int tasks,unsigned long long*records,unsigned*roster){
 unsigned sm=smid();if(threadIdx.x==0)roster[blockIdx.x*2]=sm;cg::this_grid().sync();
 if(sm==target)for(int j=0;j<tasks;j++){int task=order[j];for(int rep=0;rep<4;rep++){
  __syncthreads();unsigned long long t=clock64(),ns=timer();
  reduce_chunk(w,d,c,count,splits,task,1,0);__syncthreads();
  unsigned long long dt=clock64()-t,dns=timer()-ns;
  if(threadIdx.x==0){long long z=((long long)target*tasks+task)*8+rep*2;records[z]=dt;records[z+1]=dns;}
 }}
 if(threadIdx.x==0)roster[blockIdx.x*2+1]=smid();
}
extern "C" __global__ void address_verify(const float*w,float*d,const float*c,int count,int splits,const int*map,int waves,float alpha,float beta,unsigned*trace){
 unsigned sm=smid();if(threadIdx.x==0){trace[blockIdx.x*2]=sm;trace[blockIdx.x*2+1]=sm;}
 cg::this_grid().sync();
 for(int wave=0;wave<waves;wave++){int task=map[sm*waves+wave];if(task>=0){reduce_chunk(w,d,c,count,splits,task,alpha,beta);if(threadIdx.x==0)trace[112+task]=sm;}}
 if(threadIdx.x==0)trace[blockIdx.x*2+1]=smid();
}
