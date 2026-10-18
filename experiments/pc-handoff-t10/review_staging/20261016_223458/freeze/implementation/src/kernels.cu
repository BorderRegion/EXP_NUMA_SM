#include "kernels.cuh"
#define DECL(I,R) \
extern "C" __global__ void p##I(typename R::P::Params p,int owner,int owners,int slab,int reverse,unsigned *trace,unsigned generation){extern __shared__ char sm[];typename R::P op;op(p,*reinterpret_cast<typename R::P::SharedStorage*>(sm),owner,owners,slab,reverse,trace,generation);} \
extern "C" __global__ void n##I(typename R::Native::Params p){extern __shared__ char sm[];typename R::Native op;op(p,*reinterpret_cast<typename R::Native::SharedStorage*>(sm));} \
extern "C" __global__ void s##I(typename R::S1::Params p){extern __shared__ char sm[];typename R::S1 op;op(p,*reinterpret_cast<typename R::S1::SharedStorage*>(sm));}
DECL(0,R0) DECL(1,R1) DECL(2,R2) DECL(3,R3)
extern "C" __global__ void r(Red::Params p,int bm,int bn,int owner,int owners,int slab,int reverse,unsigned*trace,unsigned generation){Red::SharedStorage sm;Red op;op(p,sm,bm,bn,owner,owners,slab,reverse,trace,generation);}
extern "C" __global__ void rn(NativeRed::Params p){NativeRed::SharedStorage sm;NativeRed op;op(p,sm);}
extern "C" __global__ void roster(unsigned *trace){
#if PC_DIAG
 unsigned sm;asm volatile("mov.u32 %0, %smid;":"=r"(sm));if(threadIdx.x==0)trace[blockIdx.x]=sm;
#endif
}
extern "C" __global__ void scratch_read(const unsigned *p,unsigned *out,unsigned n){unsigned s=0;for(unsigned i=blockIdx.x*blockDim.x+threadIdx.x;i<n;i+=gridDim.x*blockDim.x)s+=p[i];out[blockIdx.x*blockDim.x+threadIdx.x]=s;}
extern "C" __global__ void silu_half(const float *p,Half*out,unsigned n){unsigned i=blockIdx.x*blockDim.x+threadIdx.x;if(i<n){float x=p[i];out[i]=Half(x/(1.f+expf(-x)));}}
