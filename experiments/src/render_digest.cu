#include "render_dispatch.h"
__global__ void screen_kernel(const float*color,const float*T,const unsigned*contrib,unsigned long long*partial,int pixels){
 unsigned long long acc=0;for(size_t i=blockIdx.x*blockDim.x+threadIdx.x;i<size_t(pixels)*5;i+=blockDim.x*gridDim.x){unsigned v=i<size_t(pixels)*3?__float_as_uint(color[i]):i<size_t(pixels)*4?__float_as_uint(T[i-pixels*3]):contrib[i-pixels*4];acc+=(unsigned long long)v*(i+1);}
 __shared__ unsigned long long s[256];s[threadIdx.x]=acc;__syncthreads();for(int k=128;k;k/=2){if(threadIdx.x<k)s[threadIdx.x]+=s[threadIdx.x+k];__syncthreads();}if(!threadIdx.x)partial[blockIdx.x]=s[0];
}
void ec_digest(const RenderArgs&a,unsigned long long*p){screen_kernel<<<256,256>>>(a.out_color,a.final_T,a.n_contrib,p,a.width*a.height);}
