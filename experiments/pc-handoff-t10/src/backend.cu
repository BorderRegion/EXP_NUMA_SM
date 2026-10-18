#include "/home/ubuntu/projects/leetgpu-lab/.venv/lib/python3.12/site-packages/nvidia/cuda_runtime/include/cuda.h"
#include "kernels.cuh"
#include "resources.hpp"
#include <cublas_v2.h>
#include <array>
#include <map>
#include <memory>
#include <cstring>
#include <sstream>
#include <algorithm>
static thread_local std::string error;
void bc(cublasStatus_t e,const char*s){if(e)throw std::runtime_error(std::string(s)+":"+std::to_string(e));}
struct Engine {
 Resources b; CUmodule mod[2]; std::map<std::string,CUfunction> fn[2]; CUstream parent; cublasHandle_t blas; CUdeviceptr blas_workspace=0;
 CUevent fork,pe[2],re[2];std::array<int,4> quad;std::array<std::array<int,2>,3> halves;
 Engine(const char*dir,int mode){
  quad.fill(-1);for(auto &x:halves)x.fill(-1);
  ck(cuCtxSetCurrent(b.primary),"primary");ck(cuStreamCreate(&parent,CU_STREAM_NON_BLOCKING),"parent");
  for(auto e:{&fork,&pe[0],&pe[1],&re[0],&re[1]})ck(cuEventCreate(e,CU_EVENT_DISABLE_TIMING),"dependency event");
  for(int d=0;d<2;d++){std::string p=std::string(dir)+"/diag"+std::to_string(d)+".cubin";ck(cuModuleLoad(&mod[d],p.c_str()),"load cubin");for(auto n:{"p0","p1","p2","p3","n0","n1","n2","n3","s0","s1","s2","s3","r","rn","roster","scratch_read","silu_half"}){CUfunction f;ck(cuModuleGetFunction(&f,mod[d],n),n);fn[d][n]=f;}}
  if(mode==-1)for(int i=0;i<4;i++){std::vector<int>v;for(int j=0;j<7;j++)v.push_back(i*7+j);quad[i]=b.merge(v);}
  const int combinations[3][2]={{0,1},{0,2},{0,3}};
  for(int p=0;p<3;p++)if(mode==-1||mode==p)for(int c=0;c<2;c++){std::vector<int>v;for(int q=0;q<4;q++)if((q==combinations[p][0]||q==combinations[p][1])==(c==0))for(int j=0;j<7;j++)v.push_back(q*7+j);halves[p][c]=b.merge(v);}
  ck(cuCtxSetCurrent(b.primary),"blas context");bc(cublasCreate(&blas),"cublas create");bc(cublasSetMathMode(blas,CUBLAS_MATH_DISALLOW_REDUCED_PRECISION_REDUCTION),"math mode");bc(cublasSetStream(blas,(cudaStream_t)parent),"blas stream");ck(cuMemAlloc(&blas_workspace,64u<<20),"blas workspace");bc(cublasSetWorkspace(blas,(void*)blas_workspace,64u<<20),"blas workspace bind");
 }
 ~Engine(){cuCtxSetCurrent(b.primary);cublasDestroy(blas);cuMemFree(blas_workspace);for(auto m:mod)cuModuleUnload(m);for(auto e:{fork,pe[0],pe[1],re[0],re[1]})cuEventDestroy(e);cuStreamDestroy(parent);}
 CUstream stream(int g){if(g<0){ck(cuCtxSetCurrent(b.primary),"native current");return parent;}b.current(g);return b.groups[g].stream;}
 void launch(const std::string&name,int diag,int g,dim3 grid,dim3 block,int shared,void**args){auto f=fn[diag].at(name);auto st=stream(g);if(shared>=48*1024)ck(cuFuncSetAttribute(f,CU_FUNC_ATTRIBUTE_MAX_DYNAMIC_SHARED_SIZE_BYTES,shared),"shared optin");ck(cuLaunchKernel(f,grid.x,grid.y,grid.z,block.x,block.y,block.z,shared,st,args,nullptr),name.c_str());}
 void gemm(const Half*a,const Half*b,float*d,int m,int n,int k){ck(cuCtxSetCurrent(this->b.primary),"blas primary");float alpha=1,beta=0;bc(cublasGemmEx(blas,CUBLAS_OP_T,CUBLAS_OP_N,n,m,k,&alpha,b,CUDA_R_16F,k,a,CUDA_R_16F,k,&beta,d,CUDA_R_32F,n,CUBLAS_COMPUTE_32F,CUBLAS_GEMM_DEFAULT_TENSOR_OP),"cublasGemmEx");}
};
struct Job {
 Engine&e;int c[20];void*p[11];float alpha,beta;CUgraph body=nullptr,wrapped=nullptr;CUgraphExec exec=nullptr,batch=nullptr;CUevent start,end,ps,pend,rs,rend,ss,se;int kernels=0;
 Job(Engine&e_,const int*cfg,void**ptr,float a,float b):e(e_),alpha(a),beta(b){std::copy(cfg,cfg+20,c);std::copy(ptr,ptr+11,p);for(auto x:{&start,&end,&ps,&pend,&rs,&rend,&ss,&se})ck(cuEventCreate(x,0),"timing event");}
 ~Job(){cuCtxSetCurrent(e.b.primary);if(exec)cuGraphExecDestroy(exec);if(batch)cuGraphExecDestroy(batch);if(wrapped)cuGraphDestroy(wrapped);if(body)cuGraphDestroy(body);for(auto x:{start,end,ps,pend,rs,rend,ss,se})cuEventDestroy(x);}
 template<class R> void prod(int group,int owner,int owners,bool native){
  int m=c[0],n=c[1],k=c[2],s=c[3],diag=c[14],slab=c[6],rev=c[12];unsigned gen=c[15];auto *tr=(unsigned*)p[5];
  cutlass::gemm::GemmCoord problem(m,n,k),grid((m+R::TB::kM-1)/R::TB::kM,(n+R::TB::kN-1)/R::TB::kN,s);
  typename R::P::Params par(problem,grid,{(Half*)p[0],Row(k)},{(Half*)p[1],Col(k)},{(float*)p[2],Row(n)},typename Convert::Params(),int64_t(m)*n);
  int nt=grid.m()*grid.n(),cut=(nt+1)/2,count=owners==2?(owner==0?cut:nt-cut):nt;if(!count)return;
  if(native){typename R::Native::Params np(problem,grid,{(Half*)p[0],Row(k)},{(Half*)p[1],Col(k)},{(float*)p[2],Row(n)},typename Convert::Params(),int64_t(m)*n);void*args[]={&np};auto gd=typename R::Native::ThreadblockSwizzle().get_grid_shape(grid);e.launch("n"+std::to_string(c[4]),diag,group,gd,dim3(R::Native::kThreadCount),sizeof(typename R::Native::SharedStorage),args);}
  else{void*args[]={&par,&owner,&owners,&slab,&rev,&tr,&gen};e.launch("p"+std::to_string(c[4]),diag,group,dim3(count,1,s),dim3(R::P::kThreadCount),sizeof(typename R::P::SharedStorage),args);}kernels++;
 }
 template<class R> void reduce(int group,int owner,int owners,bool native){
  int m=c[0],n=c[1],s=c[3],bm=R::TB::kM,bn=R::TB::kN,slab=c[6],rev=0,diag=c[14]; /* Task-order intervention changes producer order only. */unsigned gen=c[15];auto*tr=(unsigned*)p[5];
  Red::Params par({m,n},s,int64_t(m)*n,{(float*)p[2],Row(n)},{(float*)p[3],Row(n)},{(float*)p[4],Row(n)},Out::Params(alpha,beta));
  int nt=((m+bm-1)/bm)*((n+bn-1)/bn),cut=(nt+1)/2,count=owners==2?(owner==0?cut:nt-cut):nt;if(!count)return;
  if(native){NativeRed::Params np({m,n},s,int64_t(m)*n,{(float*)p[2],Row(n)},{(float*)p[3],Row(n)},{(float*)p[4],Row(n)},Out::Params(alpha,beta));void*args[]={&np};e.launch("rn",diag,group,NativeRed::grid_shape({m,n}),NativeRed::block_shape(),0,args);}
  else{void*args[]={&par,&bm,&bn,&owner,&owners,&slab,&rev,&tr,&gen};int base=owners==2&&owner==1?cut:0,tn=(n+bn-1)/bn,tail_start=((m+bm-1)/bm-1)*tn;
   int full_tiles=owners==2?(tail_start+1-owner)/2:tail_start,tail_rows=(m-(tail_start/tn)*bm+3)/4,cols=(bn+127)/128;
   int blocks=(full_tiles*((bm+3)/4)+(count-full_tiles)*tail_rows)*cols;
   e.launch("r",diag,group,dim3(blocks),dim3(std::min(bn,128)/4,4),0,args);}kernels++;
 }
 template<class R> void single(){
  typename R::Normal::Arguments a({c[0],c[1],c[2]},{(Half*)p[0],Row(c[2])},{(Half*)p[1],Col(c[2])},{(float*)p[4],Row(c[1])},{(float*)p[3],Row(c[1])},Out::Params(alpha,beta));
  auto grid=typename R::Normal::ThreadblockSwizzle().get_tiled_shape(a.problem_size,{R::TB::kM,R::TB::kN,R::TB::kK},1);
  typename R::S1::Params par(a.problem_size,grid,a.ref_A.non_const_ref(),a.ref_B.non_const_ref(),a.ref_C.non_const_ref(),a.ref_D,a.epilogue,nullptr);
  void*args[]={&par};auto gd=typename R::Normal::ThreadblockSwizzle().get_grid_shape(grid);e.launch("s"+std::to_string(c[4]),c[14],-1,gd,dim3(R::S1::kThreadCount),sizeof(typename R::S1::SharedStorage),args);kernels++;
 }
 template<class R> void capture(){
  auto parent=e.stream(-1);ck(cuStreamBeginCapture(parent,CU_STREAM_CAPTURE_MODE_GLOBAL),"capture begin");
  bool stages=c[19],controlled=c[5]==1,cell=c[5]==2;
  if(c[5]==3){e.gemm((Half*)p[0],(Half*)p[1],(float*)p[3],c[0],c[1],c[2]);kernels++;}
  else if(c[5]==4)single<R>();
  else if(controlled||cell){
   int branches=controlled?2:1,owners=controlled?2:1;
   if(stages)ck(cuEventRecordWithFlags(ps,e.stream(-1),CU_EVENT_RECORD_EXTERNAL),"P stage start");
   ck(cuEventRecord(e.fork,e.stream(-1)),"fork");
   for(int i=0;i<branches;i++){int g=c[11]?(branches-1-i):i;int pg=c[7+g];auto st=e.stream(pg);ck(cuStreamWaitEvent(st,e.fork,0),"P fork wait");prod<R>(pg,g,owners,false);ck(cuEventRecord(e.pe[g],st),"P done");}
   // All producers finish before either reducer, unless the explicit F1 branch is selected.
   if(!c[16]||stages||c[13])for(int g=0;g<branches;g++)ck(cuStreamWaitEvent(e.stream(-1),e.pe[g],0),"global P ready");
   if(stages)ck(cuEventRecordWithFlags(pend,e.stream(-1),CU_EVENT_RECORD_EXTERNAL),"P stage end");
   if(c[13]){if(stages)ck(cuEventRecordWithFlags(ss,e.stream(-1),CU_EVENT_RECORD_EXTERNAL),"scratch start");unsigned n=128u*1024*1024/4;void*args[]={&p[6],&p[7],&n};e.launch("scratch_read",0,-1,dim3(256),dim3(128),0,args);kernels++;if(stages)ck(cuEventRecordWithFlags(se,e.stream(-1),CU_EVENT_RECORD_EXTERNAL),"scratch end");ck(cuEventRecord(e.fork,e.stream(-1)),"scratch ready");}
   if(stages)ck(cuEventRecordWithFlags(rs,e.stream(-1),CU_EVENT_RECORD_EXTERNAL),"R start");
   for(int i=0;i<branches;i++){int g=c[11]?(branches-1-i):i;int cg=c[9+g];auto st=e.stream(cg);if(c[13])ck(cuStreamWaitEvent(st,e.fork,0),"scratch wait");else for(int j=0;j<branches;j++)if(!c[16]||j==g)ck(cuStreamWaitEvent(st,e.pe[j],0),"R dependency");if(stages)ck(cuStreamWaitEvent(st,rs,0),"R diagnostic start dependency");reduce<R>(cg,g,owners,false);ck(cuEventRecord(e.re[g],st),"R done");}
   for(int g=0;g<branches;g++)ck(cuStreamWaitEvent(e.stream(-1),e.re[g],0),"join");if(stages)ck(cuEventRecordWithFlags(rend,e.stream(-1),CU_EVENT_RECORD_EXTERNAL),"R end");
  }else{
   if(stages)ck(cuEventRecordWithFlags(ps,e.stream(-1),CU_EVENT_RECORD_EXTERNAL),"P start");
   if(c[5]!=7)prod<R>(-1,0,1,c[5]==0||c[5]==6);
   if(stages){ck(cuEventRecordWithFlags(pend,e.stream(-1),CU_EVENT_RECORD_EXTERNAL),"P end");ck(cuEventRecordWithFlags(rs,e.stream(-1),CU_EVENT_RECORD_EXTERNAL),"R start");}
   if(c[5]!=6)reduce<R>(-1,0,1,c[5]==0||c[5]==7);
   if(stages)ck(cuEventRecordWithFlags(rend,e.stream(-1),CU_EVENT_RECORD_EXTERNAL),"R end");
  }
  if(c[17]){unsigned n=c[0]*c[1];void*args[]={&p[3],&p[8],&n};e.launch("silu_half",0,-1,dim3((n+255)/256),dim3(256),0,args);e.gemm((Half*)p[8],(Half*)p[9],(float*)p[10],c[0],c[18],c[1]);kernels+=2;}
  ck(cuStreamEndCapture(e.stream(-1),&body),"capture end");ck(cuGraphInstantiate(&batch,body,0),"body instantiate");
  ck(cuGraphCreate(&wrapped,0),"timed graph");CUgraphNode a,b,z;ck(cuGraphAddEventRecordNode(&a,wrapped,nullptr,0,start),"start node");ck(cuGraphAddChildGraphNode(&b,wrapped,&a,1,body),"body node");ck(cuGraphAddEventRecordNode(&z,wrapped,&b,1,end),"end node");ck(cuGraphInstantiate(&exec,wrapped,0),"timed instantiate");
 }
 void build(){switch(c[4]){case 0:capture<R0>();break;case 1:capture<R1>();break;case 2:capture<R2>();break;case 3:capture<R3>();break;default:throw std::runtime_error("recipe");}}
 void run(double*out){e.stream(-1);auto t=Clock::now();ck(cuGraphLaunch(exec,e.parent),"timed replay");ck(cuStreamSynchronize(e.parent),"output ready");out[1]=ms(t,Clock::now())*1000;float x;ck(cuEventElapsedTime(&x,start,end),"GPU span");out[0]=x*1000;out[2]=out[3]=out[4]=-1;if(c[19]&&c[5]!=3&&c[5]!=4){ck(cuEventElapsedTime(&x,ps,pend),"P span");out[2]=x*1000;ck(cuEventElapsedTime(&x,rs,rend),"R span");out[3]=x*1000;if(c[13]){ck(cuEventElapsedTime(&x,ss,se),"scratch span");out[4]=x*1000;}}}
 void repeat(int count,double*out){e.stream(-1);auto t=Clock::now();ck(cuEventRecord(start,e.parent),"batch start");for(int i=0;i<count;i++)ck(cuGraphLaunch(batch,e.parent),"batch replay");ck(cuEventRecord(end,e.parent),"batch end");ck(cuStreamSynchronize(e.parent),"batch ready");out[1]=ms(t,Clock::now())*1000;float x;ck(cuEventElapsedTime(&x,start,end),"batch time");out[0]=x*1000;}
};
#define TRY try{error.clear();
#define CATCH }catch(const std::exception&x){error=x.what();return -1;}return 0;
extern "C" const char*pc_error(){return error.c_str();}
extern "C" void*pc_create(const char*dir,int mode){try{return new Engine(dir,mode);}catch(const std::exception&x){error=x.what();return nullptr;}}
extern "C" int pc_destroy(Engine*e){TRY delete e;CATCH}
extern "C" int pc_groups(Engine*e,int*out){TRY for(int i=0;i<4;i++)out[i]=e->quad[i];for(int i=0;i<3;i++)for(int j=0;j<2;j++)out[4+2*i+j]=e->halves[i][j];CATCH}
extern "C" int pc_roster(Engine*e,int group,unsigned*device,unsigned*host,int count){TRY void*args[]={&device};e->launch("roster",1,group,dim3(count),dim3(128),0,args);ck(cuStreamSynchronize(e->b.groups[group].stream),"roster ready");e->stream(-1);ck(cuMemcpyDtoH(host,(CUdeviceptr)device,count*sizeof(unsigned)),"roster copy");CATCH}
extern "C" Job*pc_build(Engine*e,const int*c,void**p,float alpha,float beta){try{auto j=std::make_unique<Job>(*e,c,p,alpha,beta);j->build();return j.release();}catch(const std::exception&x){error=x.what();return nullptr;}}
extern "C" int pc_drop(Job*j){TRY delete j;CATCH}
extern "C" int pc_run(Job*j,double*out){TRY j->run(out);CATCH}
extern "C" int pc_batch(Job*j,int n,double*out){TRY j->repeat(n,out);CATCH}
extern "C" int pc_nodes(Job*j,int*out){TRY size_t n=0;ck(cuGraphGetNodes(j->body,nullptr,&n),"node count");std::vector<CUgraphNode> nodes(n);ck(cuGraphGetNodes(j->body,nodes.data(),&n),"nodes");out[0]=0;for(auto node:nodes){CUgraphNodeType type;ck(cuGraphNodeGetType(node,&type),"node type");if(type==CU_GRAPH_NODE_TYPE_KERNEL)out[0]++;}out[1]=n;CATCH}

extern "C" int pc_setup_costs(Engine*e,double*out){TRY out[0]=e->b.driver_init_ms;out[1]=e->b.enumeration_ms;out[2]=e->b.green_create_ms;out[3]=e->b.groups.size();CATCH}
static thread_local std::string dag_text;
extern "C" const char*pc_dag_json(Job*j){
 try{
  size_t n=0;ck(cuGraphGetNodes(j->body,nullptr,&n),"DAG nodes");std::vector<CUgraphNode>nodes(n);ck(cuGraphGetNodes(j->body,nodes.data(),&n),"DAG nodes");std::map<CUgraphNode,int>ids;for(int i=0;i<int(n);i++)ids[nodes[i]]=i;
  // Avoid locale/iostream runtime interaction in a ctypes-loaded CUDA library.
  std::string o="{\"nodes\":[";
  for(int i=0;i<int(n);i++){
   if(i)o+=',';CUgraphNodeType type;ck(cuGraphNodeGetType(nodes[i],&type),"DAG node type");o+="{\"id\":"+std::to_string(i)+",\"type\":"+std::to_string(int(type));
   if(type==CU_GRAPH_NODE_TYPE_KERNEL){
    CUDA_KERNEL_NODE_PARAMS p{};ck(cuGraphKernelNodeGetParams(nodes[i],&p),"DAG kernel parameters");const char*name=nullptr;
    if(p.func)cuFuncGetName(&name,p.func);else if(p.kern)cuKernelGetName(&name,p.kern);
    o+=",\"function\":\""+std::string(name?name:"UNKNOWN")+"\",\"grid\":["+std::to_string(p.gridDimX)+","+std::to_string(p.gridDimY)+","+std::to_string(p.gridDimZ)+"],\"block\":["+std::to_string(p.blockDimX)+","+std::to_string(p.blockDimY)+","+std::to_string(p.blockDimZ)+"],\"shared_bytes\":"+std::to_string(p.sharedMemBytes);
   }
   o+='}';
  }
  o+="],\"edges\":[";size_t ne=0;ck(cuGraphGetEdges(j->body,nullptr,nullptr,&ne),"DAG edge count");std::vector<CUgraphNode>from(ne),to(ne);ck(cuGraphGetEdges(j->body,from.data(),to.data(),&ne),"DAG edges");
  for(int i=0;i<int(ne);i++){if(i)o+=',';o+="["+std::to_string(ids.at(from[i]))+","+std::to_string(ids.at(to[i]))+"]";}
  o+="],\"timed_wrapper\":\"start-event -> child-body -> end-event\"}";dag_text=o;return dag_text.c_str();
 }catch(const std::exception&x){error=x.what();return nullptr;}
}
