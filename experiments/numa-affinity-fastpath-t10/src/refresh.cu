#include <cuda_runtime.h>
__global__ void copy_logits(const float*src,float*dst,int n){for(int i=blockIdx.x*blockDim.x+threadIdx.x;i<n;i+=blockDim.x*gridDim.x)dst[i]=src[i];}
extern "C" int copy_launch(const float*src,float*dst,int n,unsigned long long stream){copy_logits<<<56,256,0,(cudaStream_t)stream>>>(src,dst,n);return int(cudaGetLastError());}
