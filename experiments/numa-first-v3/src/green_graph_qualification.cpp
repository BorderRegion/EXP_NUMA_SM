#include "driver_backend.hpp"
#include "probe_types.hpp"
#include <fstream>
#include <iostream>
#include <set>
#include <vector>
int main(int argc,char**argv){try{
 std::string out=argv[1],cubin=argv[2];Backend b(1);CUmodule mod;ck(cuModuleLoad(&mod,cubin.c_str()),"module");CUfunction f;ck(cuModuleGetFunction(&f,mod,"parity_consume"),"function");unsigned rw=512,win=32,mask=1,bias=0,lx=0;int cg=1,reps=1;Buffer data(64*512*4),sums(64*8),d0(32*sizeof(ProbeRecord)),d1(32*sizeof(ProbeRecord));std::vector<unsigned>h(data.bytes/4);for(unsigned i=0;i<h.size();i++)h[i]=i;data.upload(h.data());std::vector<uint64_t>expected(64);for(unsigned r=0;r<64;r++)for(unsigned k=0;k<rw;k++)expected[r]+=((k/win)*64+r)*win+k%win;
 CUstream parent;ck(cuStreamCreate(&parent,CU_STREAM_NON_BLOCKING),"parent");CUevent fork,finish;ck(cuEventCreate(&fork,0),"fork");ck(cuEventCreate(&finish,0),"finish");
 auto launch=[&](unsigned g){b.current(g);CUdeviceptr dp=g?d1.p:d0.p;void*args[]={&data.p,&sums.p,&dp,&rw,&win,&mask,&bias,&g,&lx,&cg,&reps};return cuLaunchKernel(f,32,1,1,128,1,1,0,b.groups[g].stream,args,nullptr);};
 std::set<unsigned>before[2],after[2];for(int g=0;g<2;g++){ck(launch(g),"direct");ck(cuStreamSynchronize(b.groups[g].stream),"ready");std::vector<ProbeRecord>v(32);(g?d1:d0).download(v.data());for(auto&x:v)before[g].insert(x.sm_begin);}ck(cuCtxSetCurrent(b.primary),"parent current");ck(cuMemsetD32(sums.p,0,128),"reset");
 CUgraph graph=nullptr;CUgraphExec executable=nullptr;CUresult status=cuStreamBeginCapture(parent,CU_STREAM_CAPTURE_MODE_GLOBAL);std::string step="begin";
 if(!status){step="fork";status=cuEventRecord(fork,parent);}
 for(unsigned g=0;g<2&&!status;g++){b.current(g);step="group wait";status=cuStreamWaitEvent(b.groups[g].stream,fork,0);if(!status){step="group launch";status=launch(g);}if(!status){step="group event";status=cuEventRecord(b.groups[g].end,b.groups[g].stream);}}
 ck(cuCtxSetCurrent(b.primary),"parent current");for(int g=0;g<2&&!status;g++){step="parent join";status=cuStreamWaitEvent(parent,b.groups[g].end,0);}if(!status){step="finish";status=cuEventRecord(finish,parent);}CUresult ended=cuStreamEndCapture(parent,&graph);if(!status){step="end capture";status=ended;}
 if(!status){step="instantiate";status=cuGraphInstantiateWithFlags(&executable,graph,0);}
 std::ofstream result(out+"/green_graph.json");
 if(status){const char*name="unknown";cuGetErrorName(status,&name);result<<"{\"status\":\"UNSUPPORTED_OR_REJECTED\",\"step\":\""<<step<<"\",\"error\":\""<<name<<"\",\"performance_claim\":false}";if(graph)cuGraphDestroy(graph);return 0;}
 size_t nodes=0;ck(cuGraphGetNodes(graph,nullptr,&nodes),"nodes");
 for(int repeat=0;repeat<8;repeat++){ck(cuGraphLaunch(executable,parent),"graph replay");ck(cuStreamSynchronize(parent),"ready");std::vector<uint64_t>v(64);sums.download(v.data());if(v!=expected)throw std::runtime_error("graph output mismatch");for(int g=0;g<2;g++){std::vector<ProbeRecord>d(32);(g?d1:d0).download(d.data());for(auto&x:d){if(x.sm_begin!=x.sm_end)throw std::runtime_error("migration");after[g].insert(x.sm_begin);}}}
 bool respected=before[0]==after[0]&&before[1]==after[1];for(unsigned sm:after[0])if(after[1].count(sm))respected=false;
 result<<"{\"status\":\"PASS\",\"actual_graph_nodes\":"<<nodes<<",\"full_output_checks\":8,\"actual_resource_sets_preserved\":"<<(respected?"true":"false")<<",\"actual_sm_sets\":[";for(int g=0;g<2;g++){if(g)result<<',';result<<'[';bool first=true;for(unsigned sm:after[g]){if(!first)result<<',';result<<sm;first=false;}result<<']';}result<<"],\"physical_domain_claim\":false}";
 cuGraphExecDestroy(executable);cuGraphDestroy(graph);cuStreamDestroy(parent);cuEventDestroy(fork);cuEventDestroy(finish);cuModuleUnload(mod);return 0;
}catch(std::exception&e){std::cerr<<e.what()<<'\n';return 2;}}
