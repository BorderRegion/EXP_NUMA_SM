#include <cuda_runtime.h>
#include <string>
template<bool CG> __device__ __forceinline__ float4 read4(const float4*p){float4 x;
 if(CG)asm volatile("ld.global.cg.v4.f32 {%0,%1,%2,%3},[%4];":"=f"(x.x),"=f"(x.y),"=f"(x.z),"=f"(x.w):"l"(p):"memory");
 else asm volatile("ld.global.v4.f32 {%0,%1,%2,%3},[%4];":"=f"(x.x),"=f"(x.y),"=f"(x.z),"=f"(x.w):"l"(p):"memory");
 return x;
}
template<bool CG> __global__ void vector_read(const float4*x,float4*out,int n,int passes){
 int tid=blockIdx.x*blockDim.x+threadIdx.x,stride=gridDim.x*blockDim.x;
 float a=0,b=0,c=0,d=0;
 for(int pass=0;pass<passes;pass++)for(int i=tid;i<n;i+=stride){auto v=read4<CG>(x+i);a+=v.x;b+=v.y;c+=v.z;d+=v.w;}
 out[tid]=make_float4(a,b,c,d);
}
__global__ void reg_fma(const float*in,float*out){
 int tid=blockIdx.x*blockDim.x+threadIdx.x;float x=in[tid%256];float a=x,b=x+1,c=x+2,d=x+3,e=x+4,f=x+5,g=x+6,h=x+7;
 #pragma unroll 1
 for(int i=0;i<128;i++){a=fmaf(a,1.0001f,x);b=fmaf(b,1.0002f,x);c=fmaf(c,1.0003f,x);d=fmaf(d,1.0004f,x);e=fmaf(e,1.0005f,x);f=fmaf(f,1.0006f,x);g=fmaf(g,1.0007f,x);h=fmaf(h,1.0008f,x);}
 float*o=out+tid*8;o[0]=a;o[1]=b;o[2]=c;o[3]=d;o[4]=e;o[5]=f;o[6]=g;o[7]=h;
}
static thread_local std::string error;
extern "C" const char*micro_error(){return error.c_str();}
extern "C" int micro_launch(void*input,void*out,int nvec,int passes,int cg,int grid,int compute,unsigned long long stream){
 if(compute)reg_fma<<<grid,128,0,(cudaStream_t)stream>>>((float*)input,(float*)out);
 else if(cg)vector_read<true><<<grid,128,0,(cudaStream_t)stream>>>((float4*)input,(float4*)out,nvec,passes);
 else vector_read<false><<<grid,128,0,(cudaStream_t)stream>>>((float4*)input,(float4*)out,nvec,passes);
 auto e=cudaGetLastError();if(e){error=cudaGetErrorString(e);return -1;}return 0;
}
