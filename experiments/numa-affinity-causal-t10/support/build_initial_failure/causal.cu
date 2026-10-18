#include <cuda_runtime.h>
#include <cooperative_groups.h>
#include <cmath>
#include <cstring>
struct Schedule {int consumer_for_sm[56];};
namespace cg=cooperative_groups;
__device__ __forceinline__ unsigned smid(){unsigned x;asm volatile("mov.u32 %0, %%smid;":"=r"(x));return x;}
__device__ __forceinline__ unsigned long long timer(){unsigned long long x;asm volatile("mov.u64 %0, %%globaltimer;":"=l"(x)::"memory");return x;}
__device__ __forceinline__ unsigned acquire(const unsigned*p){unsigned x;asm volatile("ld.acquire.gpu.global.u32 %0,[%1];":"=r"(x):"l"(p):"memory");return x;}
__device__ __forceinline__ void release(unsigned*p,unsigned x){asm volatile("st.release.gpu.global.u32 [%0],%1;"::"l"(p),"r"(x):"memory");}
__device__ __forceinline__ float loadcg(const float*p){float x;asm volatile("ld.global.cg.f32 %0,[%1];":"=f"(x):"l"(p):"memory");return x;}
__device__ __forceinline__ float wmax(float x){for(int d=16;d;d/=2)x=fmaxf(x,__shfl_xor_sync(0xffffffff,x,d));return x;}
__device__ __forceinline__ float wsum(float x){for(int d=16;d;d/=2)x+=__shfl_xor_sync(0xffffffff,x,d);return x;}
__device__ float bmax(float x,float*s){int lane=threadIdx.x%32,warp=threadIdx.x/32;x=wmax(x);if(!lane)s[warp]=x;__syncthreads();x=lane<4?s[lane]:-INFINITY;x=wmax(x);__syncthreads();return x;}
__device__ float bsum(float x,float*s){int lane=threadIdx.x%32,warp=threadIdx.x/32;x=wsum(x);if(!lane)s[warp]=x;__syncthreads();x=lane<4?s[lane]:0;x=wsum(x);__syncthreads();return x;}
__device__ bool waitfor(const unsigned*p,unsigned value,unsigned long long deadline){unsigned polls=0;while(acquire(p)!=value){if((++polls&63)==0&&timer()>deadline)return false;}return true;}

// One real softmax per launch; no repeated artificial communication work.
template<int V,bool Trace,bool Balanced,bool Fixed> __global__ void paired(const float*x,float*y,unsigned*flags,Schedule schedule,int page,int*trace,unsigned long long*prof){
 extern __shared__ unsigned char reserve[];float*sh=(float*)reserve;
 __shared__ int islast,failed;
 unsigned sm=smid(),t=threadIdx.x,lane=t%32;
 unsigned*ctrl=flags+400*1024;unsigned*box=flags+(page+(sm/2))*1024;
 if(t==0){failed=0;islast=0;if(sm%2==0)box[0]=0;if(sm==0){ctrl[0]=ctrl[1]=ctrl[2]=0;}if(Trace){trace[2*blockIdx.x]=sm;trace[2*blockIdx.x+1]=sm;}}
 // Cooperative launch plus one CTA occupancy makes the SM roster a bijection.
 cg::this_grid().sync();
 constexpr int R=(V+56*128-1)/(56*128);
 int count=Balanced?V/56+(sm<unsigned(V%56)):0;
 int start=sm*(V/56)+(sm<unsigned(V%56)?sm:V%56);
 if(Trace&&t==0){for(int j=0;j<10;j++)prof[sm*10+j]=0;prof[sm*10]=sm;prof[sm*10+2]=Balanced?count:((V>int(sm*128))?((V-sm*128)/(56*128))*128+min(128,int((V-sm*128)%(56*128))):0);prof[sm*10+3]=timer();prof[sm*10+9]=sm%2?schedule.consumer_for_sm[sm]:sm/2;}
 float reg[R],m=-INFINITY;
 #pragma unroll
 for(int i=0;i<R;i++){int idx=Balanced?start+t+i*128:sm*128+t+i*56*128;bool valid=Balanced?(int(t+i*128)<count):(idx<V);reg[i]=valid?x[idx]:-INFINITY;m=fmaxf(m,reg[i]);}
 m=bmax(m,sh);float s=0;
 #pragma unroll
 for(int i=0;i<R;i++){reg[i]=expf(reg[i]-m);s+=reg[i];}
 s=bsum(s,sh);
 if(Trace&&t==0)prof[sm*10+4]=timer();
 if(t==0){
  auto deadline=timer()+1000000000ull;
  if(sm%2==0){float*p=(float*)(box+64);p[0]=m;p[1]=s;release(box,1);}
  else{
   int source=schedule.consumer_for_sm[sm];box=flags+(page+source)*1024;
   if(!waitfor(box,1,deadline)){failed=1;atomicOr(ctrl+2,1);}
   float*p=(float*)(box+64);float a=loadcg(p),b=loadcg(p+1),mm=fmaxf(m,a);
   float*out=(float*)(box+128);out[0]=mm;out[1]=s*expf(m-mm)+b*expf(a-mm);
   __threadfence();unsigned old;asm volatile("atom.acq_rel.gpu.global.add.u32 %0,[%1],1;":"=r"(old):"l"(ctrl):"memory");if(!Fixed)islast=old==27;
  }
  if(Trace)prof[sm*10+5]=timer();
  if(Fixed&&sm==1){if(!waitfor(ctrl,28,deadline)){failed=1;atomicOr(ctrl+2,4);}islast=1;}
 }
 __syncthreads();
 if(islast){
  if(Trace&&t==0)prof[sm*10+6]=timer();
  if(t<32){float mm=lane<28?loadcg((float*)(flags+(page+lane)*1024+128)):-INFINITY;float mx=wmax(mm);float z=lane<28?loadcg((float*)(flags+(page+lane)*1024+129))*expf(mm-mx):0;z=wsum(z);if(lane==0){((float*)ctrl)[4]=mx;((float*)ctrl)[5]=z;release(ctrl+1,1);if(Trace)prof[sm*10+7]=timer();}}
 }
 if(t==0){if(!waitfor(ctrl+1,1,timer()+1000000000ull)){failed=1;atomicOr(ctrl+2,2);}}
 __syncthreads();float mx=loadcg((float*)ctrl+4),sum=loadcg((float*)ctrl+5);float scale=expf(m-mx)/sum;
 #pragma unroll
 for(int i=0;i<R;i++){int idx=Balanced?start+t+i*128:sm*128+t+i*56*128;if(Balanced?(int(t+i*128)<count):(idx<V))y[idx]=failed?NAN:reg[i]*scale;}
 if(Trace&&t==0){trace[2*blockIdx.x+1]=smid();prof[sm*10+1]=smid();prof[sm*10+8]=timer();}
}

template<int V> __global__ void partial(const float*x,float*p){
 __shared__ float sh[4];int t=threadIdx.x;constexpr int R=(V+56*128-1)/(56*128);
 int count=Balanced?V/56+(sm<unsigned(V%56)):0;
 int start=sm*(V/56)+(sm<unsigned(V%56)?sm:V%56);
 if(Trace&&t==0){for(int j=0;j<10;j++)prof[sm*10+j]=0;prof[sm*10]=sm;prof[sm*10+2]=Balanced?count:((V>int(sm*128))?((V-sm*128)/(56*128))*128+min(128,int((V-sm*128)%(56*128))):0);prof[sm*10+3]=timer();prof[sm*10+9]=sm%2?schedule.consumer_for_sm[sm]:sm/2;}
 float reg[R],m=-INFINITY;
 #pragma unroll
 for(int i=0;i<R;i++){int idx=blockIdx.x*128+t+i*56*128;reg[i]=idx<V?x[idx]:-INFINITY;m=fmaxf(m,reg[i]);}
 m=bmax(m,sh);float s=0;
 #pragma unroll
 for(int i=0;i<R;i++)s+=expf(reg[i]-m);
 s=bsum(s,sh);if(!t){p[2*blockIdx.x]=m;p[2*blockIdx.x+1]=s;}
}
template<int V> __global__ void finish(const float*x,float*y,const float*p){
 int lane=threadIdx.x%32;float m=-INFINITY;
 for(int i=lane;i<56;i+=32)m=fmaxf(m,p[2*i]);m=wmax(m);float s=0;
 for(int i=lane;i<56;i+=32)s+=p[2*i+1]*expf(p[2*i]-m);s=wsum(s);
 for(int idx=blockIdx.x*128+threadIdx.x;idx<V;idx+=56*128)y[idx]=expf(x[idx]-m)/s;
}
static thread_local const char*error_message="";
extern "C" const char*sf_error(){return error_message;}
template<int V,bool Trace,bool Balanced,bool Fixed> cudaError_t execute(const float*x,float*y,unsigned*flags,Schedule schedule,int page,int*trace,float*p,unsigned long long*prof,int mode,cudaStream_t stream){
 if(mode==0){partial<V><<<56,128,0,stream>>>(x,p);finish<V><<<56,128,0,stream>>>(x,y,p);return cudaGetLastError();}
 auto err=cudaFuncSetAttribute(paired<V,Trace,Balanced,Fixed>,cudaFuncAttributeMaxDynamicSharedMemorySize,48*1024);if(err!=cudaSuccess)return err;
 int active=0;err=cudaOccupancyMaxActiveBlocksPerMultiprocessor(&active,paired<V,Trace,Balanced,Fixed>,128,48*1024);if(err!=cudaSuccess)return err;if(active!=1)return cudaErrorInvalidConfiguration;
 void*args[]={&x,&y,&flags,&schedule,&page,&trace,&prof};return cudaLaunchCooperativeKernel((void*)paired<V,Trace,Balanced,Fixed>,56,128,args,48*1024,stream);
}

template<int V,bool T> cudaError_t dispatch(void**a,int*c,unsigned long long st){
 #define EXEC(B,F) execute<V,T,B,F>((float*)a[0],(float*)a[1],(unsigned*)a[2],schedule,c[2],(int*)a[4],(float*)a[5],(unsigned long long*)a[6],c[1],(cudaStream_t)st)
 Schedule schedule;std::memcpy(&schedule,a[3],sizeof(schedule));
 if(c[1]<=1)return EXEC(false,false);
 if(c[1]==2)return EXEC(true,false);
 if(c[1]==3)return EXEC(false,true);
 if(c[1]==4)return EXEC(true,true);
 return cudaErrorInvalidValue;
 #undef EXEC
}
extern "C" int sf_launch(void**a,int*c,unsigned long long st){
 cudaError_t e=cudaErrorInvalidValue;
 #define CASE(V) if(c[0]==V){e=c[3]?dispatch<V,true>(a,c,st):dispatch<V,false>(a,c,st);}
 CASE(131072) else CASE(129024)
 if(e!=cudaSuccess){error_message=cudaGetErrorString(e);return -1;}return 0;
}
