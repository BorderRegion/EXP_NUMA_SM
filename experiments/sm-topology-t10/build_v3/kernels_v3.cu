#include <cuda_runtime.h>
#include <cooperative_groups.h>
#include "types.hpp"
namespace cg=cooperative_groups;
__device__ __forceinline__ unsigned smid(){unsigned v;asm volatile("mov.u32 %0, %%smid;":"=r"(v));return v;}
__device__ __forceinline__ unsigned long long timer(){unsigned long long v;asm volatile("mov.u64 %0, %%globaltimer;":"=l"(v)::"memory");return v;}
__device__ __forceinline__ unsigned acquire(const unsigned*p){unsigned v;asm volatile("ld.acquire.gpu.global.u32 %0,[%1];":"=r"(v):"l"(p):"memory");return v;}
__device__ __forceinline__ void release(unsigned*p,unsigned v){asm volatile("st.release.gpu.global.u32 [%0],%1;"::"l"(p),"r"(v):"memory");}
__device__ __forceinline__ unsigned loadcg(const unsigned*p){unsigned v;asm volatile("ld.global.cg.u32 %0,[%1];":"=r"(v):"l"(p):"memory");return v;}
__device__ __forceinline__ unsigned loadca(const unsigned*p){unsigned v;asm volatile("ld.global.ca.u32 %0,[%1];":"=r"(v):"l"(p):"memory");return v;}
__device__ __forceinline__ void storecg(unsigned*p,unsigned v){asm volatile("st.global.cg.u32 [%0],%1;"::"l"(p),"r"(v):"memory");}
__device__ bool waitfor(const unsigned*p,unsigned v,unsigned long long deadline){
 unsigned polls=0;while(acquire(p)!=v){if((++polls&63)==0 && timer()>deadline)return false;}return true;
}
// Source-clock round trip: no subtraction of clocks from different SMs.
// In kind 1, exactly one pair is active; other SMs return after initial grid sync.
// In kind 3, all 28 producer/consumer pairs execute the identical payload work.
extern "C" __global__ void probe(unsigned*flags,const unsigned*chain,const unsigned*starts,
 Record*rec,Plan p,const int*map){
 extern __shared__ volatile unsigned char residency[];
 residency[threadIdx.x]=(unsigned char)threadIdx.x;
 unsigned sm=smid(),tid=threadIdx.x;
 if(tid==0){rec->roster_begin[blockIdx.x]=sm;rec->roster_end[blockIdx.x]=sm;}
 unsigned offsets[3]={0,17*4096,257*4096};
 unsigned*base=flags+p.slot*1024;
 if(p.kind==3)base=flags+(p.slot+blockIdx.x)*1024;
 if(tid==0 && (blockIdx.x==0 || p.kind==3)){storecg(base,0);storecg(base+32,0);}
 cg::this_grid().sync();
 if(p.kind==0)return;
 if(p.kind==2){
  if(tid!=0||int(sm)!=p.src)return;
  unsigned idx=starts[p.region];
  for(int i=0;i<256;i++)idx=p.mode?loadca(chain+idx):loadcg(chain+idx);
  unsigned sb=smid();auto t=timer();auto c=clock64();
  #pragma unroll 1
  for(int i=0;i<p.steps;i++)idx=p.mode?loadca(chain+idx):loadcg(chain+idx);
  auto c1=clock64();auto t1=timer();
  rec->ns=t1-t;rec->cycles=c1-c;rec->src_begin=sb;rec->src_end=smid();rec->src_value=idx;
  rec->roster_end[blockIdx.x]=smid();return;
 }
 int role=-1;
 if(p.kind==1){
  if(tid==0&&int(sm)==p.src)role=0;
  if(int(sm)==p.dst&&tid==(p.src==p.dst?32:0))role=1;
 }else if(p.kind==3){
  // map[sm*2] = stable logical pair ID; map[sm*2+1] = role.
  if(tid==0){role=map[sm*2+1];base=flags+(p.slot+map[sm*2])*1024;}
 }
 if(role<0)return;
 Record*rr=p.kind==3 ? rec+map[sm*2] : rec;
 unsigned*req=base,*ack=base+32,*payload=base+64;
 unsigned sb=smid(),errors=0,last=0;
 auto deadline=timer()+10000000ull;
 unsigned long long t=0,c=0;
 constexpr unsigned warm=16;
 for(unsigned seq=1;seq<=unsigned(p.steps)+warm;seq++){
  if(seq==warm+1){t=timer();c=clock64();}
  if(role==0){
   if(p.mode){
    #pragma unroll
    for(unsigned j=0;j<16;j++)storecg(payload+j,seq*17+j);
   }
   release(req,seq);
   if(!waitfor(ack,seq,deadline)){errors|=1;break;}
   last=seq;
  }else{
   if(!waitfor(req,seq,deadline)){errors|=2;break;}
   if(p.mode){unsigned sum=0;
    #pragma unroll
    for(unsigned j=0;j<16;j++)sum+=loadcg(payload+j);
    if(sum!=seq*272+120)errors|=4;
   }
   release(ack,seq);last=seq;
  }
 }
 auto c1=clock64();auto t1=timer();unsigned se=smid();
 if(role==0){rr->ns=t1-t;rr->cycles=c1-c;rr->src_begin=sb;rr->src_end=se;rr->src_value=last;}
 else {rr->peer_ns=t1-t;rr->peer_cycles=c1-c;rr->dst_begin=sb;rr->dst_end=se;rr->dst_value=last;}
 if(errors)atomicOr(&rr->errors,errors);
 if(tid==0)rec->roster_end[blockIdx.x]=se;
}
