#include <cuda_runtime.h>
extern "C" __global__ void spmv_rows(const int*row,const int*col,const float*x,float*y,int n,const int*table,int task_count,int rows_per_task,int native_mode,unsigned*visits){
 int warp=threadIdx.x/32,lane=threadIdx.x%32;
 for(int q=blockIdx.x;q<task_count;q+=gridDim.x){int task=table?table[q]:q;int first=task*rows_per_task,last=min(n,first+rows_per_task);
  for(int r=first+warp;r<last;r+=blockDim.x/32){float sum=0;for(int j=row[r]+lane;j<row[r+1];j+=32)sum+=x[col[j]];for(int d=16;d;d/=2)sum+=__shfl_down_sync(0xffffffff,sum,d);if(!lane){y[r]=sum;if(visits)atomicAdd(visits+r,1);}}
  if(native_mode)break;
 }
}
extern "C" __global__ void vector_input(float*x,int n,unsigned seed){for(int i=blockIdx.x*blockDim.x+threadIdx.x;i<n;i+=blockDim.x*gridDim.x)x[i]=float((unsigned(i)*1664525u+seed*1013904223u)%32);}
extern "C" __global__ void sparse_digest(const float*y,unsigned long long*partial,int n){unsigned long long v=0;for(int i=blockIdx.x*blockDim.x+threadIdx.x;i<n;i+=blockDim.x*gridDim.x)v+=(unsigned long long)__float_as_uint(y[i])*(i+1);__shared__ unsigned long long s[256];s[threadIdx.x]=v;__syncthreads();for(int k=128;k;k/=2){if(threadIdx.x<k)s[threadIdx.x]+=s[threadIdx.x+k];__syncthreads();}if(!threadIdx.x)partial[blockIdx.x]=s[0];}
