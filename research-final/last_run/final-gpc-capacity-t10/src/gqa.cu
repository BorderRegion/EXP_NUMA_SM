#include "/home/ubuntu/projects/leetgpu-lab/.venv/lib/python3.12/site-packages/nvidia/cuda_runtime/include/cuda.h"
#include <cuda_runtime.h>
#include <cuda_fp16.h>
#include <cmath>
#include <string>
#include <vector>
#include <map>
#include <chrono>
#include <stdexcept>
struct Params {const half *q,*k,*v;const int *table,*length,*list;unsigned *counter;float *partial;half *out;int *trace;int B,HK,NP,W,mode;};
namespace stage26 {
__device__ __forceinline__ unsigned smid(){unsigned x;asm volatile("mov.u32 %0, %%smid;":"=r"(x));return x;}
__device__ __forceinline__ float wmax(float x){for(int d=16;d;d/=2)x=fmaxf(x,__shfl_xor_sync(0xffffffff,x,d));return x;}
__device__ __forceinline__ float wsum(float x){for(int d=16;d;d/=2)x+=__shfl_xor_sync(0xffffffff,x,d);return x;}
__device__ __forceinline__ float cg(const float*p){float x;asm volatile("ld.global.cg.f32 %0,[%1];":"=f"(x):"l"(p):"memory");return x;}
__device__ __forceinline__ unsigned arrival(unsigned*p){unsigned x;asm volatile("atom.acq_rel.gpu.global.add.u32 %0,[%1],1;":"=r"(x):"l"(p):"memory");return x;}
template<int D,int G> __device__ void merge_head(Params p,int head,float* weights){
 int lane=threadIdx.x%32,g=threadIdx.x/32;float m=-INFINITY;
 for(int w=lane;w<p.W;w+=32)m=fmaxf(m,cg(p.partial+((head*p.W+w)*G+g)*(D+4)+D));m=wmax(m);
 float mass=0;
 for(int w=lane;w<p.W;w+=32){float a=expf(cg(p.partial+((head*p.W+w)*G+g)*(D+4)+D)-m);weights[g*128+w]=a;mass+=a;}
 float z=wsum(mass);__syncwarp();
 #pragma unroll
 for(int j=0;j<D/32;j++){int d=lane+j*32;float out=0;
  for(int s=0;s<p.W;s++)out=fmaf(weights[g*128+s],cg(p.partial+((head*p.W+s)*G+g)*(D+4)+d),out);
  p.out[(head*G+g)*D+d]=__float2half_rn(out/z);
 }
 __syncthreads();if(threadIdx.x==0){p.counter[head*3]=0;p.counter[head*3+1]=0;p.counter[head*3+2]=0;}
}
template<int D,int G,bool Queue,bool Fused,bool Trace> __global__ void decode(Params p){
 const int head=blockIdx.x/p.W,worker=blockIdx.x%p.W,b=head/p.HK,hk=head%p.HK;
 int lane=threadIdx.x%32,g=threadIdx.x/32,sm=Trace?smid():0;int pref=worker&1;
 __shared__ int page,source,last;
 extern __shared__ unsigned char buf[];half*ks=(half*)buf;half*vs=ks+16*(D+8);float* score=(float*)(vs+16*(D+8));
 half2 qr[D/8];
 #pragma unroll
 for(int j=0;j<D/8;j++)qr[j]=*((const half2*)(p.q+(head*G+g)*D+(lane%4)*2+j*8));
 float acc[D/32];
 #pragma unroll
 for(int j=0;j<D/32;j++)acc[j]=0;
 float am=-INFINITY,al=0;int iteration=0;
 while(true){
  if(threadIdx.x==0){
   if(Queue){const int*ls=p.list+head*(p.NP+2);int which=pref;unsigned i=atomicAdd(p.counter+head*3+which,1);if(i>=unsigned(ls[which])){which^=1;i=atomicAdd(p.counter+head*3+which,1);}page=i<unsigned(ls[which])?ls[2+(which?ls[0]:0)+i]:-1;source=which;}
   else {page=worker+iteration*p.W;if(page>=p.NP)page=-1;source=-1;}
   if(Trace&&page>=0){int t=head*p.NP+page;int*tr=p.trace+5*t;tr[0]=sm;tr[1]=worker;tr[2]=Queue?pref:-1;tr[3]=source;atomicAdd(tr+4,1);}
  }
  __syncthreads();if(page<0)break;
  if(page*16<p.length[b]){
   int physical=p.table[b*p.NP+page];long long base=((long long)physical*p.HK+hk)*16*D;
   for(int i=threadIdx.x;i<16*(D/8);i+=blockDim.x){int tok=i/(D/8),d=i%(D/8);bool valid=page*16+tok<p.length[b];((uint4*)ks)[tok*((D+8)/8)+d]=valid?((const uint4*)(p.k+base))[i]:make_uint4(0,0,0,0);((uint4*)vs)[tok*((D+8)/8)+d]=valid?((const uint4*)(p.v+base))[i]:make_uint4(0,0,0,0);}
   __syncthreads();
   #pragma unroll
   for(int t=0;t<2;t++){int tok=lane/4+8*t;float dot=0;
    #pragma unroll
    for(int j=0;j<D/8;j++){half2 kv=*((half2*)(ks+tok*(D+8)+(lane%4)*2+j*8));float2 qf=__half22float2(qr[j]),kf=__half22float2(kv);dot=fmaf(qf.x,kf.x,dot);dot=fmaf(qf.y,kf.y,dot);}
    dot+=__shfl_xor_sync(0xffffffff,dot,1,4);dot+=__shfl_xor_sync(0xffffffff,dot,2,4);
    if((lane%4)==0)score[g*16+tok]=page*16+tok<p.length[b]?dot*rsqrtf(float(D)):-INFINITY;
   }
   __syncwarp();float x=lane<16?score[g*16+lane]:-INFINITY;float pm=wmax(x);float w=lane<16?expf(x-pm):0;float pl=wsum(w);if(lane<16)score[g*16+lane]=w;__syncwarp();
   float nm=fmaxf(am,pm),old_scale=al>0?expf(am-nm):0,new_scale=expf(pm-nm);
   #pragma unroll
   for(int j=0;j<D/32;j++){int d=lane+j*32;float o=0;
    #pragma unroll
    for(int t=0;t<16;t++)o=fmaf(score[g*16+t],__half2float(vs[t*(D+8)+d]),o);
    acc[j]=fmaf(acc[j],old_scale,o*new_scale);
   }
   al=al*old_scale+pl*new_scale;am=nm;
  }
  __syncthreads();iteration++;
 }
 float*dst=p.partial+((head*p.W+worker)*G+g)*(D+4);
 #pragma unroll
 for(int j=0;j<D/32;j++)dst[lane+j*32]=al>0?acc[j]/al:0;
 if(lane==0){dst[D]=al>0?am+logf(al):-INFINITY;dst[D+1]=dst[D+2]=dst[D+3]=0;}
 if(Fused){__threadfence();__syncthreads();if(threadIdx.x==0)last=arrival(p.counter+head*3+2)==unsigned(p.W-1);__syncthreads();if(last)merge_head<D,G>(p,head,score);}
}
template<int D,int G> __global__ void merge(Params p){__shared__ float w[G*128];merge_head<D,G>(p,blockIdx.x,w);}
template<int D,int G,bool Fused,bool Trace> void run_typed(Params p,cudaStream_t stream){
 int blocks=p.B*p.HK*p.W,smem=16*(D+8)*4+G*128*4;
 if(p.mode==0)decode<D,G,false,Fused,Trace><<<blocks,32*G,smem,stream>>>(p);
 else decode<D,G,true,Fused,Trace><<<blocks,32*G,smem,stream>>>(p);
 if(!Fused)merge<D,G><<<p.B*p.HK,32*G,0,stream>>>(p);
}
template<int D,int G> void route(Params p,int fused,int trace,cudaStream_t stream){
 if(fused){if(trace)run_typed<D,G,true,true>(p,stream);else run_typed<D,G,true,false>(p,stream);}
 else{if(trace)run_typed<D,G,false,true>(p,stream);else run_typed<D,G,false,false>(p,stream);}
}
static thread_local std::string err;
extern "C" const char*ll_error(){return err.c_str();}
extern "C" int ll_launch(void**a,const int*c,unsigned long long stream){
 if(c[6]!=0 && c[6]!=1){err="Only original DIRECT/BLIND allowed";return -1;}
 Params p{(half*)a[0],(half*)a[1],(half*)a[2],(int*)a[3],(int*)a[4],(int*)a[5],(unsigned*)a[6],(float*)a[7],(half*)a[8],(int*)a[9],c[2],c[3],c[4],c[5],c[6]};
 #define GO(D,G) if(c[0]==D&&c[1]==G)route<D,G>(p,c[7],c[8],(cudaStream_t)stream)
 GO(128,1);else GO(128,4);else GO(128,8);else GO(256,4);else {err="unsupported D,G";return -1;}
 auto e=cudaGetLastError();if(e!=cudaSuccess){err=cudaGetErrorString(e);return -1;}return 0;
}
void ck(CUresult x,const char*s){if(x!=CUDA_SUCCESS){const char*p=nullptr;cuGetErrorString(x,&p);throw std::runtime_error(std::string(s)+":"+(p?p:"unknown"));}}
struct Timed {CUgraph graph=nullptr;CUgraphExec exec=nullptr;CUevent begin=nullptr,end=nullptr;CUstream stream=nullptr;
 Timed(void*body){ck(cuStreamCreate(&stream,CU_STREAM_NON_BLOCKING),"stream");ck(cuEventCreate(&begin,0),"event");ck(cuEventCreate(&end,0),"event");ck(cuGraphCreate(&graph,0),"graph");CUgraphNode a,b,c;ck(cuGraphAddEventRecordNode(&a,graph,nullptr,0,begin),"start");ck(cuGraphAddChildGraphNode(&b,graph,&a,1,(CUgraph)body),"body");ck(cuGraphAddEventRecordNode(&c,graph,&b,1,end),"end");ck(cuGraphInstantiate(&exec,graph,0),"instantiate");}
 ~Timed(){if(exec)cuGraphExecDestroy(exec);if(graph)cuGraphDestroy(graph);if(begin)cuEventDestroy(begin);if(end)cuEventDestroy(end);if(stream)cuStreamDestroy(stream);}
 void run(int n,double*out){for(int i=0;i<n;i++){auto t=std::chrono::steady_clock::now();ck(cuGraphLaunch(exec,stream),"launch");ck(cuStreamSynchronize(stream),"output ready");auto dt=std::chrono::steady_clock::now()-t;out[2*i+1]=std::chrono::duration<double,std::micro>(dt).count();float x;ck(cuEventElapsedTime(&x,begin,end),"elapsed");out[2*i]=x*1000;}}
};
extern "C" void*ll_timed(void*body){try{return new Timed(body);}catch(std::exception&e){err=e.what();return nullptr;}}
extern "C" int ll_repeat(Timed*p,int n,double*out){try{p->run(n,out);return 0;}catch(std::exception&e){err=e.what();return -1;}}
extern "C" void ll_drop(Timed*p){delete p;}
static thread_local std::string dag;
extern "C" const char*ll_dag(void*raw){try{CUgraph graph=(CUgraph)raw;size_t n=0;ck(cuGraphGetNodes(graph,nullptr,&n),"nodes");std::vector<CUgraphNode> nodes(n);ck(cuGraphGetNodes(graph,nodes.data(),&n),"nodes");std::map<CUgraphNode,int> ids;for(int i=0;i<int(n);i++)ids[nodes[i]]=i;dag="{\"nodes\":[";
 for(int i=0;i<int(n);i++){if(i)dag+=',';CUgraphNodeType type;ck(cuGraphNodeGetType(nodes[i],&type),"type");dag+="{\"id\":"+std::to_string(i)+",\"type\":"+std::to_string(int(type));if(type==CU_GRAPH_NODE_TYPE_KERNEL){CUDA_KERNEL_NODE_PARAMS p{};ck(cuGraphKernelNodeGetParams(nodes[i],&p),"params");const char*name=nullptr;if(p.func)cuFuncGetName(&name,p.func);else if(p.kern)cuKernelGetName(&name,p.kern);dag+=",\"function\":\""+std::string(name?name:"UNKNOWN")+"\",\"grid\":["+std::to_string(p.gridDimX)+","+std::to_string(p.gridDimY)+","+std::to_string(p.gridDimZ)+"],\"block\":["+std::to_string(p.blockDimX)+","+std::to_string(p.blockDimY)+","+std::to_string(p.blockDimZ)+"],\"shared_bytes\":"+std::to_string(p.sharedMemBytes);}dag+='}';}
 dag+="],\"edges\":[";size_t ne=0;ck(cuGraphGetEdges(graph,nullptr,nullptr,&ne),"edges");std::vector<CUgraphNode> a(ne),b(ne);if(ne)ck(cuGraphGetEdges(graph,a.data(),b.data(),&ne),"edges");for(int i=0;i<int(ne);i++){if(i)dag+=',';dag+="["+std::to_string(ids.at(a[i]))+","+std::to_string(ids.at(b[i]))+"]";}dag+="]}";return dag.c_str();}catch(std::exception&e){err=e.what();return nullptr;}}

}
