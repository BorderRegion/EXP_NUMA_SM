// CUTLASS 3.5.1 SM75 grouped math with original or packet visitor.
#include <cuda_runtime.h>
#include <cstdint>
#include <type_traits>
#include "cutlass/gemm/kernel/default_gemm_grouped.h"
#include "cutlass/gemm/device/gemm_grouped.h"
#include "packet_visitor.h"
#include "q1_minimal.h"
#include "cutlass/gemm/device/gemm.h"
#include "op_fused_gemm_grouped.h"

using namespace cutlass;
using namespace cutlass::gemm;
constexpr auto DeviceOnly=kernel::GroupScheduleMode::kDeviceOnly;
template<int BM,int BN> struct Math {
  using Original=typename kernel::DefaultGemmGrouped<
    half_t,layout::RowMajor,ComplexTransform::kNone,8,
    half_t,layout::RowMajor,ComplexTransform::kNone,8,
    half_t,layout::RowMajor,float,arch::OpClassTensorOp,arch::Sm75,
    GemmShape<BM,BN,32>,GemmShape<32,BN/2,32>,GemmShape<16,8,8>,
    epilogue::thread::LinearCombination<half_t,8,float,float>,
    threadblock::GemmBatchedIdentityThreadblockSwizzle,2,DeviceOnly>::GemmKernel;
  template<bool Full> using Visitor=kernel::OpPacketVisitor<
    kernel::detail::GemmGroupedProblemSizeHelper<GemmShape<BM,BN,32>,false>,
    GemmShape<BM,BN,32>,Original::kThreadCount,Original::kThreadCount,Full>;
  template<bool Full> using Packet=kernel::OpFusedGemmGrouped<
    typename Original::Mma,typename Original::Epilogue,
    typename Original::ThreadblockSwizzle,DeviceOnly,Visitor<Full>,false>;
  using Minimal=kernel::OpFusedGemmGrouped<typename Original::Mma,typename Original::Epilogue,typename Original::ThreadblockSwizzle,DeviceOnly,kernel::Q1MinimalVisitor<GemmShape<BM,BN,32>,Original::kThreadCount>,false>;
  template<int Mode> using Select=std::conditional_t<Mode==0,Original,std::conditional_t<Mode==3,Minimal,Packet<Mode==2>>>;
  using Single=device::Gemm<half_t,layout::RowMajor,half_t,layout::RowMajor,half_t,layout::RowMajor,float,arch::OpClassTensorOp,arch::Sm75,GemmShape<BM,BN,32>,GemmShape<32,BN/2,32>,GemmShape<16,8,8>,epilogue::thread::LinearCombination<half_t,8,float,float>,threadblock::GemmIdentityThreadblockSwizzle<>,2,8,8,false>;
};
struct Handle {virtual int run(cudaStream_t)=0;virtual ~Handle()=default;};
template<typename K,bool Packet> struct Runner:Handle,device::GemmGrouped<K> {
  using Op=device::GemmGrouped<K>;
  int run(cudaStream_t stream) override {return int(Op::run(stream));}
  void policy(int q,int waves,int budget,const int *sideband) {
    if constexpr(Packet) {
      this->params_.problem_visitor.q_cap=q;
      this->params_.problem_visitor.target_waves=waves;
      this->params_.problem_visitor.work_budget=budget;
      this->params_.problem_visitor.sideband_total=sideband;
    }
  }
};

template<typename K,bool P> void *make(int count,int workers,int q,int waves,int budget,
  void *shapes,void *ap,void *bp,void *cp,void *lda,void *ldb,void *ldc,void *sideband,int *status) {
  auto *h=new Runner<K,P>();
  typename K::Arguments args(reinterpret_cast<GemmCoord*>(shapes),count,workers,
    {1.0f,0.0f},reinterpret_cast<half_t**>(ap),reinterpret_cast<half_t**>(bp),
    reinterpret_cast<half_t**>(cp),reinterpret_cast<half_t**>(cp),
    reinterpret_cast<int64_t*>(lda),reinterpret_cast<int64_t*>(ldb),
    reinterpret_cast<int64_t*>(ldc),reinterpret_cast<int64_t*>(ldc));
  *status=int(h->initialize(args));
  if (*status) {delete h;return nullptr;}
  h->policy(q,waves,budget,reinterpret_cast<const int*>(sideband));return h;
}

template<typename K> int resource(int *out) {
  cudaFuncAttributes attributes{};
  int code=int(cudaFuncGetAttributes(&attributes,cutlass::Kernel<K>));if(code)return code;
  int dev=0,sm=0;cudaGetDevice(&dev);cudaDeviceGetAttribute(&sm,cudaDevAttrMultiProcessorCount,dev);
  out[0]=device::GemmGrouped<K>::maximum_active_blocks();out[1]=K::kThreadCount;
  out[2]=sizeof(typename K::SharedStorage);out[3]=attributes.numRegs;out[4]=sm;
  out[5]=K::ThreadblockShape::kM;out[6]=K::ThreadblockShape::kN;out[7]=K::ThreadblockShape::kK;
  return out[0]>0?0:1;
}

extern "C" int opf_resources(int recipe,int mode,int *out) {
  if(recipe<0 || recipe>3 || mode<0 || mode>3)return -1;
#define RES(BM,BN) if(mode==0)return resource<typename Math<BM,BN>::Original>(out); \
 if(mode==1)return resource<typename Math<BM,BN>::template Packet<false>>(out); \
 if(mode==2)return resource<typename Math<BM,BN>::template Packet<true>>(out); \
 return resource<typename Math<BM,BN>::Minimal>(out);
  switch(recipe){case 0:{RES(32,128)} case 1:{RES(64,128)} case 2:{RES(32,64)} default:{RES(64,64)}}
#undef RES
}
extern "C" void *opf_create(int recipe,int mode,int count,int workers,int q,int waves,int budget,
  void *shapes,void *ap,void *bp,void *cp,void *lda,void *ldb,void *ldc,void *sideband,int *status) {
  if(recipe<0 || recipe>3 || mode<0 || mode>3 || count<=0 || workers<=0 ||
     (q!=1 && q!=2 && q!=4) || (waves!=1 && waves!=2) || budget<=0) {*status=-1;return nullptr;}
#define MAKE(BM,BN) if(mode==0)return make<typename Math<BM,BN>::Original,false>(count,workers,q,waves,budget,shapes,ap,bp,cp,lda,ldb,ldc,sideband,status); \
 if(mode==1)return make<typename Math<BM,BN>::template Packet<false>,true>(count,workers,q,waves,budget,shapes,ap,bp,cp,lda,ldb,ldc,sideband,status); \
 if(mode==2)return make<typename Math<BM,BN>::template Packet<true>,true>(count,workers,q,waves,budget,shapes,ap,bp,cp,lda,ldb,ldc,sideband,status); \
 return make<typename Math<BM,BN>::Minimal,false>(count,workers,q,waves,budget,shapes,ap,bp,cp,lda,ldb,ldc,sideband,status);
  switch(recipe){case 0:{MAKE(32,128)} case 1:{MAKE(64,128)} case 2:{MAKE(32,64)} default:{MAKE(64,64)}}
#undef MAKE
}
extern "C" int opf_run(void *p,void *stream) {
  return p?static_cast<Handle*>(p)->run(reinterpret_cast<cudaStream_t>(stream)):-1;
}
extern "C" void opf_destroy(void *p) {delete static_cast<Handle*>(p);}

// Qualification only. This kernel is never called by a production timing path.
template<int BM,int BN,int Mode> __global__ void count_visits(
  typename Math<BM,BN>::template Select<Mode>::ProblemVisitor::Params params,
  const int *prefix,int *counts) {
  using K=typename Math<BM,BN>::template Select<Mode>;
  using V=typename K::ProblemVisitor;
  __shared__ typename V::SharedStorage storage;
  V visitor(params,storage,blockIdx.x);
  while(visitor.next_tile()) {
    if(threadIdx.x==0) atomicAdd(counts+prefix[visitor.problem_index()]+visitor.threadblock_idx(),1);
    visitor.advance(gridDim.x);
  }
}
template<int BM,int BN,int Mode> int launch_count(int n,int workers,int q,int waves,
  void *shapes,void *prefix,void *counts,void *stream) {
  using K=typename Math<BM,BN>::template Select<Mode>;
  typename K::ProblemVisitor::Params params(reinterpret_cast<GemmCoord*>(shapes),n);
  if constexpr(Mode==1 || Mode==2) {params.q_cap=q;params.target_waves=waves;params.work_budget=128;}
  count_visits<BM,BN,Mode><<<workers,K::kThreadCount,0,reinterpret_cast<cudaStream_t>(stream)>>>(
    params,reinterpret_cast<const int*>(prefix),reinterpret_cast<int*>(counts));
  return int(cudaGetLastError());
}
extern "C" int opf_count_visits(int recipe,int mode,int n,int workers,int q,int waves,
  void *shapes,void *prefix,void *counts,void *stream) {
  if(recipe<0 || recipe>3 || mode<0 || mode>3 || workers<=0)return -1;
#define COUNT(BM,BN) if(mode==0)return launch_count<BM,BN,0>(n,workers,q,waves,shapes,prefix,counts,stream); \
 if(mode==1)return launch_count<BM,BN,1>(n,workers,q,waves,shapes,prefix,counts,stream); \
 if(mode==2)return launch_count<BM,BN,2>(n,workers,q,waves,shapes,prefix,counts,stream); \
 return launch_count<BM,BN,3>(n,workers,q,waves,shapes,prefix,counts,stream);
  switch(recipe){case 0:{COUNT(32,128)} case 1:{COUNT(64,128)} case 2:{COUNT(32,64)} default:{COUNT(64,64)}}
#undef COUNT
}

// Same useful pack for F0/F1. F1 additionally writes O(1) shape sideband from
// already-ready device problem sizes. No other CTA's output is read here.
template<bool Sideband> __global__ void pack_rows(
  const uint4 *input,const int64_t *token,uint4 *output,int rows,int width8,
  const GemmCoord *up,const GemmCoord *down,int experts,int bm,int bn,int *totals) {
  int count=rows*width8;
  for(int i=blockIdx.x*blockDim.x+threadIdx.x;i<count;i+=gridDim.x*blockDim.x) {
    int row=i/width8,col=i%width8;
    output[i]=input[token[row]*width8+col];
  }
  if constexpr(Sideband) {
    if(blockIdx.x==0 && threadIdx.x<32) {
      int a=0,b=0,lane=threadIdx.x;
      for(int e=lane;e<experts;e+=32) {
        auto u=up[e],d=down[e];
        a+=((u.m()+bm-1)/bm)*((u.n()+bn-1)/bn);
        b+=((d.m()+bm-1)/bm)*((d.n()+bn-1)/bn);
      }
      for(int off=16;off>0;off/=2) {
        a+=__shfl_down_sync(0xffffffff,a,off);b+=__shfl_down_sync(0xffffffff,b,off);
      }
      if(lane==0) {totals[0]=a;totals[1]=b;}
    }
  }
}
extern "C" int opf_pack(int sideband,void *input,void *token,void *output,
  int rows,int width,void *up,void *down,int experts,int bm,int bn,void *totals,void *stream) {
  if(rows<=0 || width<=0 || width%8 || (bm!=32 && bm!=64) || (bn!=64 && bn!=128))return -1;
  int blocks=(rows*(width/8)+255)/256;
#define PACK(S) pack_rows<S><<<blocks,256,0,reinterpret_cast<cudaStream_t>(stream)>>>( \
    reinterpret_cast<const uint4*>(input),reinterpret_cast<const int64_t*>(token), \
    reinterpret_cast<uint4*>(output),rows,width/8,reinterpret_cast<const GemmCoord*>(up), \
    reinterpret_cast<const GemmCoord*>(down),experts,bm,bn,reinterpret_cast<int*>(totals));
  if(sideband){PACK(true)}else{PACK(false)}
#undef PACK
  return int(cudaGetLastError());
}

// Ordinary single GEMM is a bounded diagnostic, never a per-expert candidate.
template<class Op> struct SingleRunner:Handle {
  Op op;
  int run(cudaStream_t stream) override {return int(op.run(stream));}
};
template<int BM,int BN> void *make_single(int m,int n,int k,void *a,void *b,void *c,int la,int lb,int lc,int *status) {
  using Op=typename Math<BM,BN>::Single;
  auto *h=new SingleRunner<Op>();
  typename Op::Arguments args({m,n,k},{reinterpret_cast<half_t*>(a),la},{reinterpret_cast<half_t*>(b),lb},{reinterpret_cast<half_t*>(c),lc},{reinterpret_cast<half_t*>(c),lc},{1.f,0.f},1);
  *status=int(h->op.initialize(args));
  if(*status){delete h;return nullptr;}return h;
}
extern "C" void *opf_single_create(int recipe,int m,int n,int k,void *a,void *b,void *c,int la,int lb,int lc,int *status) {
#define SINGLE(BM,BN) return make_single<BM,BN>(m,n,k,a,b,c,la,lb,lc,status);
  switch(recipe){case 0:{SINGLE(32,128)} case 1:{SINGLE(64,128)} case 2:{SINGLE(32,64)} case 3:{SINGLE(64,64)} default:*status=-1;return nullptr;}
#undef SINGLE
}
