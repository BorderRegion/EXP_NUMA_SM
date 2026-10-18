#include <cuda_runtime.h>
#include <cooperative_groups.h>
#include <cmath>
#include <cstring>
namespace cg=cooperative_groups;
struct Schedule {int map[56];};
struct Delays {unsigned long long ns[56];};
struct Record {
 unsigned long long start[56],arrived[56],paired[56],done[56];
 unsigned collector[56],observed[56],errors[56];
 float maximum[56],sum[56];
};
static_assert(sizeof(Record)==2912);
__device__ __forceinline__ unsigned smid(){unsigned v;asm volatile("mov.u32 %0, %%smid;":"=r"(v));return v;}
__device__ __forceinline__ unsigned long long timer(){unsigned long long v;asm volatile("mov.u64 %0, %%globaltimer;":"=l"(v)::"memory");return v;}
__device__ __forceinline__ unsigned acquire(const unsigned*p){unsigned v;asm volatile("ld.acquire.gpu.global.u32 %0,[%1];":"=r"(v):"l"(p):"memory");return v;}
__device__ __forceinline__ void release(unsigned*p,unsigned v){asm volatile("st.release.gpu.global.u32 [%0],%1;"::"l"(p),"r"(v):"memory");}
__device__ __forceinline__ float loadcg(const float*p){float v;asm volatile("ld.global.cg.f32 %0,[%1];":"=f"(v):"l"(p):"memory");return v;}
__device__ bool waitfor(const unsigned*p,unsigned v,unsigned long long deadline){unsigned n=0;while(acquire(p)!=v){if((++n&63)==0&&timer()>deadline)return false;}return true;}
__device__ float wmax(float x){for(int d=16;d;d/=2)x=fmaxf(x,__shfl_xor_sync(0xffffffff,x,d));return x;}
__device__ float wsum(float x){for(int d=16;d;d/=2)x+=__shfl_xor_sync(0xffffffff,x,d);return x;}

// One complete communication tail per launch, including fan-in and broadcast.
// Delays model observed local-compute arrival differences. No Softmax output
// timing from this probe is used as an operator speedup measurement.
__global__ void tail(unsigned*flags,Record*r,Schedule schedule,int page,Delays delays){
 extern __shared__ volatile unsigned char reserve[];
 reserve[threadIdx.x]=(unsigned char)threadIdx.x;
 __shared__ int islast;
 unsigned sm=smid(),t=threadIdx.x,lane=t%32,err=0;
 unsigned*ctrl=flags+400*1024;unsigned*box=flags+(page+sm/2)*1024;
 if(t==0){islast=0;if(sm%2==0)box[0]=0;if(sm==0)ctrl[0]=ctrl[1]=ctrl[2]=0;}
 cg::this_grid().sync();
 unsigned long long start=0,arrived=0,paired=0,done=0;
 float m=float(sm)/56.0f,s=100.0f+float(sm);
 if(t==0){
  start=timer();while(timer()-start<delays.ns[sm]){}arrived=timer();
  auto deadline=timer()+10000000ull;
  if(sm%2==0){float*p=(float*)(box+64);p[0]=m;p[1]=s;release(box,1);}
  else{
   box=flags+(page+schedule.map[sm])*1024;
   if(!waitfor(box,1,deadline)){err|=1;atomicOr(ctrl+2,1);}
   float a=loadcg((float*)(box+64)),b=loadcg((float*)(box+65)),mm=fmaxf(a,m);
   float*out=(float*)(box+128);out[0]=mm;out[1]=s*expf(m-mm)+b*expf(a-mm);
   __threadfence();unsigned old;asm volatile("atom.acq_rel.gpu.global.add.u32 %0,[%1],1;":"=r"(old):"l"(ctrl):"memory");islast=old==27;
  }
  paired=timer();
 }
 __syncthreads();
 if(islast&&t<32){
  float mm=lane<28?loadcg((float*)(flags+(page+lane)*1024+128)):-INFINITY;float mx=wmax(mm);
  float z=lane<28?loadcg((float*)(flags+(page+lane)*1024+129))*expf(mm-mx):0;z=wsum(z);
  if(lane==0){((float*)ctrl)[4]=mx;((float*)ctrl)[5]=z;release(ctrl+1,1);}
 }
 float mx=0,z=0;
 if(t==0){if(!waitfor(ctrl+1,1,timer()+10000000ull)){err|=2;atomicOr(ctrl+2,2);}mx=loadcg((float*)ctrl+4);z=loadcg((float*)ctrl+5);done=timer();}
 // Diagnostic stores occur only after every SM completed the measured tail.
 cg::this_grid().sync();
 if(t==0){r->start[sm]=start;r->arrived[sm]=arrived;r->paired[sm]=paired;r->done[sm]=done;r->collector[sm]=islast;r->observed[sm]=smid();r->errors[sm]=err;r->maximum[sm]=mx;r->sum[sm]=z;}
}
static thread_local const char*message="";
extern "C" const char*tail_error(){return message;}
// host plans: [offset_pages,page,family,round]; host schedules: family x56.
extern "C" int tail_batch(void*flags,void*records,const int*plans,const int*maps,const unsigned long long*waits,int n,unsigned long long st){
 cudaError_t e=cudaFuncSetAttribute(tail,cudaFuncAttributeMaxDynamicSharedMemorySize,48*1024);int active=0;
 if(e==cudaSuccess)e=cudaOccupancyMaxActiveBlocksPerMultiprocessor(&active,tail,128,48*1024);
 if(e==cudaSuccess&&active!=1)e=cudaErrorInvalidConfiguration;
 Delays delay;std::memcpy(&delay,waits,sizeof(delay));
 for(int i=0;i<n&&e==cudaSuccess;i++){
  const int*p=plans+4*i;unsigned*base=(unsigned*)flags+p[0]*1024;Record*r=(Record*)records+i;
  Schedule schedule;std::memcpy(&schedule,maps+p[2]*56,sizeof(schedule));int page=p[1];
  void*args[]={&base,&r,&schedule,&page,&delay};
  e=cudaLaunchCooperativeKernel((void*)tail,56,128,args,48*1024,(cudaStream_t)st);
 }
 if(e!=cudaSuccess){message=cudaGetErrorString(e);return -1;}return 0;
}
