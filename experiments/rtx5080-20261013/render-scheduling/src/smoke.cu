#include <cuda_runtime.h>
#include <cstdio>
#include <cstdint>
#include <vector>
#include <stdexcept>
#define CK(x) do { cudaError_t ck_status=(x); if(ck_status!=cudaSuccess) {std::fprintf(stderr,"%s: %s\n",#x,cudaGetErrorString(ck_status));return 2;} } while(0)
__global__ void transform(const uint32_t* x,uint32_t* y,int n){int i=blockIdx.x*blockDim.x+threadIdx.x;if(i<n)y[i]=(x[i]^0xa5a5a5a5u)*1664525u+1013904223u;}
int main(){constexpr int n=32768;std::vector<uint32_t> x(n),y(n);for(int i=0;i<n;i++)x[i]=i*2654435761u;uint32_t *a,*b;CK(cudaMalloc(&a,n*4));CK(cudaMalloc(&b,n*4));CK(cudaMemcpy(a,x.data(),n*4,cudaMemcpyHostToDevice));cudaEvent_t s,e;CK(cudaEventCreate(&s));CK(cudaEventCreate(&e));CK(cudaEventRecord(s));transform<<<(n+255)/256,256>>>(a,b,n);CK(cudaGetLastError());CK(cudaEventRecord(e));CK(cudaEventSynchronize(e));float ms;CK(cudaEventElapsedTime(&ms,s,e));CK(cudaMemcpy(y.data(),b,n*4,cudaMemcpyDeviceToHost));int errors=0;uint64_t checksum=0;for(int i=0;i<n;i++){errors+=y[i]!=((x[i]^0xa5a5a5a5u)*1664525u+1013904223u);checksum+=y[i];}int driver,runtime;CK(cudaDriverGetVersion(&driver));CK(cudaRuntimeGetVersion(&runtime));cudaDeviceProp p;CK(cudaGetDeviceProperties(&p,0));std::printf("{\"n\":%d,\"errors\":%d,\"checksum\":%llu,\"kernel_ms\":%.6f,\"driver\":%d,\"runtime\":%d,\"device\":\"%s\",\"cc\":\"%d.%d\",\"sm_count\":%d,\"l2_bytes\":%d}\n",n,errors,(unsigned long long)checksum,ms,driver,runtime,p.name,p.major,p.minor,p.multiProcessorCount,p.l2CacheSize);CK(cudaFree(a));CK(cudaFree(b));CK(cudaEventDestroy(s));CK(cudaEventDestroy(e));return errors?1:0;}
