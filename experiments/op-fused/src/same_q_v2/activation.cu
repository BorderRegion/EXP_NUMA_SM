#include <cuda_runtime.h>
#include <cuda_fp16.h>
#include <cmath>
// Runs after the complete up GEMM in the same stream. Preserve the original
// half SiLU materialization before multiplying, then round the product to half.
__global__ void silu_multiply_half_boundaries(const __half *gu,__half *out,int rows,int width) {
  int count=rows*width;
  for(int i=blockIdx.x*blockDim.x+threadIdx.x;i<count;i+=blockDim.x*gridDim.x) {
    int row=i/width,col=i%width;
    float x=__half2float(gu[row*width*2+col]);
    __half s=__float2half_rn(x/(1.0f+expf(-x)));
    float u=__half2float(gu[row*width*2+width+col]);
    out[i]=__float2half_rn(__half2float(s)*u);
  }
}
extern "C" int opf_activation(void *gu,void *out,int rows,int width,void *stream) {
  if(rows<=0 || width<=0)return -1;
  silu_multiply_half_boundaries<<<(rows*width+255)/256,256,0,reinterpret_cast<cudaStream_t>(stream)>>>(
      reinterpret_cast<const __half*>(gu),reinterpret_cast<__half*>(out),rows,width);
  return int(cudaGetLastError());
}
