#include "kernels.cuh"
#include <cuda_runtime.h>
__device__ __forceinline__ unsigned smid(){unsigned v;asm volatile("mov.u32 %0, %%smid;":"=r"(v));return v;}
__device__ __forceinline__ float4 load_cg(const float*p){float4 v;asm volatile("ld.global.cg.v4.f32 {%0,%1,%2,%3}, [%4];":"=f"(v.x),"=f"(v.y),"=f"(v.z),"=f"(v.w):"l"(p):"memory");return v;}
__device__ __forceinline__ float4 reduce_vector(const float*w,int count,int splits,int i){
 float4 a=make_float4(0,0,0,0);
 // Issue four independent split loads before consuming them, matching native ILP.
 for(int base=0;base<splits;base+=4){float4 x[4];
  #pragma unroll
  for(int t=0;t<4;t++)if(base+t<splits)x[t]=load_cg(w+(long long)(base+t)*count+i);
  #pragma unroll
  for(int t=0;t<4;t++)if(base+t<splits){a.x+=x[t].x;a.y+=x[t].y;a.z+=x[t].z;a.w+=x[t].w;}
 }
 return a;
}
__device__ __forceinline__ void store_result(float4 a,float*d,const float*c,int i,float alpha,float beta){
 float4 b=make_float4(0,0,0,0);if(beta!=0)b=*((const float4*)(c+i));
 *((float4*)(d+i))=make_float4(alpha*a.x+beta*b.x,alpha*a.y+beta*b.y,alpha*a.z+beta*b.z,alpha*a.w+beta*b.w);
}
__device__ void reduce_chunk(const float*w,float*d,const float*c,int count,int splits,int task,int chunk,float alpha,float beta){
 for(int i=task*chunk+threadIdx.x*4;i<min((task+1)*chunk,count);i+=blockDim.x*4)store_result(reduce_vector(w,count,splits,i),d,c,i,alpha,beta);
}
#define RARGS const float*w,float*d,const float*c,int count,int splits,const int*list,unsigned*counters,int chunk,int mode,float alpha,float beta,unsigned*trace
#define RPASS w,d,c,count,splits,list,counters,chunk,mode,alpha,beta,trace
extern "C" __global__ void direct_reduce(RARGS){reduce_chunk(w,d,c,count,splits,blockIdx.x,chunk,alpha,beta);}
template<bool Trace> __device__ void queue_body(RARGS){
 __shared__ int task,source;unsigned sm=smid();int pref=mode==0?(int(blockIdx.x)&1):(((sm%10>=4)&&(sm%10<=7))?1:0);if(mode==2)pref^=1;
 int total=(count+chunk-1)/chunk;
 while(true){
  if(threadIdx.x==0){unsigned i=atomicAdd(counters+pref,1);source=pref;int q=pref;
   if(i>=unsigned(list[q])){q^=1;i=atomicAdd(counters+q,1);source=q;}
   task=i<unsigned(list[q])?list[2+(q?list[0]:0)+i]:-1;
   if(Trace&&task>=0){trace[task*4]=sm;trace[task*4+1]=pref;trace[task*4+2]=source;trace[task*4+3]=blockIdx.x;atomicAdd(trace+total*4+task,1);}
  }
  __syncthreads();if(task<0)return;
  reduce_chunk(w,d,c,count,splits,task,chunk,alpha,beta);__syncthreads();
 }
}
extern "C" __global__ void queue_reduce(RARGS){queue_body<false>(RPASS);}
extern "C" __global__ void queue_trace(RARGS){queue_body<true>(RPASS);}

// Counter initialization is part of the producer launch, before the reducer starts.
template<class R> __device__ void reset_producer(typename R::Native::Params p,typename R::Native::SharedStorage&sm,unsigned*counters){
 if(blockIdx.x==0&&blockIdx.y==0&&blockIdx.z==0&&threadIdx.x<2)counters[threadIdx.x]=0;
 typename R::Native op;op(p,sm);
}
#define PROD(I,R) extern "C" __global__ void q##I(typename R::Native::Params p,unsigned*counters){extern __shared__ char sm[];reset_producer<R>(p,*reinterpret_cast<typename R::Native::SharedStorage*>(sm),counters);}
PROD(0,R0) PROD(2,R2)

__device__ unsigned arrive(unsigned*p){unsigned old;asm volatile("atom.acq_rel.gpu.global.add.u32 %0, [%1], 1;":"=r"(old):"l"(p):"memory");return old;}
template<class R,bool Trace> __device__ void fused_body(typename R::Native::Params p,typename R::Native::SharedStorage&sm,float*d,const float*c,unsigned*counters,float alpha,float beta,unsigned*trace){
 auto tile=typename R::Native::ThreadblockSwizzle().get_tile_offset(p.swizzle_log_tile);
 if(tile.m()>=p.grid_tiled_shape.m()||tile.n()>=p.grid_tiled_shape.n())return;
 typename R::Native op;op(p,sm);
 // Every lane publishes its own epilogue stores, then thread 0 publishes CTA arrival.
 __threadfence();__syncthreads();
 __shared__ unsigned last;
 int tid=tile.m()*p.grid_tiled_shape.n()+tile.n(),nt=p.grid_tiled_shape.m()*p.grid_tiled_shape.n(),splits=p.grid_tiled_shape.k();
 if(threadIdx.x==0){unsigned old=arrive(counters+tid);last=old==unsigned(splits-1);if(Trace){trace[(tid*splits+tile.k())*2]=smid();trace[(tid*splits+tile.k())*2+1]=old;}}
 __syncthreads();
 if(last){
  int n=p.problem_size.n(),m=p.problem_size.m(),valid_rows=min(R::TB::kM,m-tile.m()*R::TB::kM),valid_cols=min(R::TB::kN,n-tile.n()*R::TB::kN);
  for(int x=threadIdx.x*4;x<valid_rows*R::TB::kN;x+=blockDim.x*4){int row=x/R::TB::kN,col=x%R::TB::kN;if(col<valid_cols){int i=(tile.m()*R::TB::kM+row)*n+tile.n()*R::TB::kN+col;store_result(reduce_vector(p.ref_D.data(),m*n,splits,i),d,c,i,alpha,beta);}}
  __syncthreads();if(threadIdx.x==0){if(Trace)trace[2*nt*splits+tid]=smid();counters[tid]=0;}
 }
}
#define FUSED(I,R) \
extern "C" __global__ void f##I(typename R::Native::Params p,float*d,const float*c,unsigned*counters,float alpha,float beta,unsigned*trace){extern __shared__ char sm[];fused_body<R,false>(p,*reinterpret_cast<typename R::Native::SharedStorage*>(sm),d,c,counters,alpha,beta,trace);} \
extern "C" __global__ void ft##I(typename R::Native::Params p,float*d,const float*c,unsigned*counters,float alpha,float beta,unsigned*trace){extern __shared__ char sm[];fused_body<R,true>(p,*reinterpret_cast<typename R::Native::SharedStorage*>(sm),d,c,counters,alpha,beta,trace);}
FUSED(0,R0) FUSED(2,R2)
