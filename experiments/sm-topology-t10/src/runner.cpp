#include <cuda.h>
#include "types.hpp"
#include <algorithm>
#include <chrono>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <map>
#include <numeric>
#include <random>
#include <set>
#include <stdexcept>
#include <vector>
void ck(CUresult e,const char*s){if(e){const char*n;cuGetErrorName(e,&n);throw std::runtime_error(std::string(s)+":"+n);}}
using Clock=std::chrono::steady_clock;
int main(int argc,char**argv){try{
 std::map<std::string,std::string>a;for(int i=1;i+1<argc;i+=2)a[argv[i]]=argv[i+1];
 std::string out=a.at("--out");std::filesystem::create_directories(out);auto begin=Clock::now();
 ck(cuInit(0),"init");CUdevice dev;CUcontext ctx;ck(cuDeviceGet(&dev,0),"device");ck(cuDevicePrimaryCtxRetain(&ctx,dev),"context");ck(cuCtxSetCurrent(ctx),"current");
 int sms,coop,shared;ck(cuDeviceGetAttribute(&sms,CU_DEVICE_ATTRIBUTE_MULTIPROCESSOR_COUNT,dev),"sms");ck(cuDeviceGetAttribute(&coop,CU_DEVICE_ATTRIBUTE_COOPERATIVE_LAUNCH,dev),"cooperative");ck(cuDeviceGetAttribute(&shared,CU_DEVICE_ATTRIBUTE_MAX_SHARED_MEMORY_PER_MULTIPROCESSOR,dev),"shared");
 if(sms!=NSM||!coop)throw std::runtime_error("Requires qualified 56-SM cooperative device");
 CUmodule mod;CUfunction fn;ck(cuModuleLoad(&mod,a.at("--cubin").c_str()),"module");ck(cuModuleGetFunction(&fn,mod,"probe"),"function");
 constexpr unsigned smem=48*1024;int active;ck(cuOccupancyMaxActiveBlocksPerMultiprocessor(&active,fn,64,smem),"occupancy");if(active!=1)throw std::runtime_error("One CTA per SM occupancy qualification failed");
 CUdeviceptr flags,chain,starts,records,mapping;constexpr size_t words=(2<<20)/4;constexpr int chunk=128;
 ck(cuMemAlloc(&flags,2<<20),"flags");ck(cuMemAlloc(&chain,2<<20),"chain");ck(cuMemAlloc(&starts,64*4),"starts");ck(cuMemAlloc(&records,chunk*28*sizeof(Record)),"records");ck(cuMemAlloc(&mapping,256*2*4),"mapping");
 std::vector<unsigned>data(words,0),first(64),nodes(256);std::mt19937 rng(20261017);
 auto physical=[](unsigned r,unsigned k){return ((k/1024)*64+r)*1024+k%1024;};
 for(unsigned r=0;r<64;r++){std::iota(nodes.begin(),nodes.end(),0);std::shuffle(nodes.begin(),nodes.end(),rng);first[r]=physical(r,nodes[0]*32);for(unsigned j=0;j<256;j++)data[physical(r,nodes[j]*32)]=physical(r,nodes[(j+1)%256]*32);}
 ck(cuMemcpyHtoD(chain,data.data(),words*4),"upload chain");ck(cuMemcpyHtoD(starts,first.data(),256),"upload starts");
 std::ofstream fixture(out+"/chain_starts.csv");fixture<<"region,index\n";for(int r=0;r<64;r++)fixture<<r<<','<<first[r]<<'\n';
 CUstream stream;ck(cuStreamCreate(&stream,CU_STREAM_NON_BLOCKING),"stream");CUevent e0,e1;ck(cuEventCreate(&e0,0),"event");ck(cuEventCreate(&e1,0),"event");
 auto launch=[&](Plan p,CUdeviceptr dest){void*args[]={&flags,&chain,&starts,&dest,&p,&mapping};ck(cuLaunchCooperativeKernel(fn,56,1,1,64,1,1,smem,stream,args),"launch");};
 ck(cuMemsetD8(records,0,sizeof(Record)),"clear roster");launch(Plan{},records);ck(cuStreamSynchronize(stream),"roster ready");Record roster{};ck(cuMemcpyDtoH(&roster,records,sizeof(roster)),"roster copy");std::set<unsigned>ids(roster.roster_begin,roster.roster_begin+NSM);if(ids.size()!=NSM||*ids.rbegin()>=256)throw std::runtime_error("Coverage qualification failed");
 std::ofstream env(out+"/environment.json");env<<"{\"sms\":"<<sms<<",\"cooperative_launch\":"<<coop<<",\"active_blocks_per_sm\":"<<active<<",\"dynamic_shared_bytes\":"<<smem<<",\"shared_per_sm\":"<<shared<<",\"flag_va\":"<<flags<<",\"chain_va\":"<<chain<<",\"roster\":[";bool comma=false;for(auto id:ids){if(comma)env<<',';env<<id;comma=true;}env<<"]}\n";env.close();
 if(a.count("--roster-only"))return 0;
 std::vector<Plan>plan;std::ifstream pf(a.at("--plan"));Plan p{};while(pf>>p.kind>>p.round>>p.mode>>p.slot>>p.src>>p.dst>>p.steps>>p.region>>p.policy)plan.push_back(p);if(plan.empty())throw std::runtime_error("Empty plan");
 std::vector<std::vector<int>>maps;
 if(a.count("--maps")){std::ifstream mf(a.at("--maps"));int np;mf>>np;maps.resize(np,std::vector<int>(512,-1));for(auto& m:maps)for(int j=0;j<28;j++){int s,d;mf>>s>>d;if(!ids.count(s)||!ids.count(d))throw std::runtime_error("Map unknown SM");m[s*2]=j;m[s*2+1]=0;m[d*2]=j;m[d*2+1]=1;}for(auto&m:maps)for(auto id:ids)if(m[id*2]<0)throw std::runtime_error("Map coverage");}
 std::ofstream raw(out+"/records.bin",std::ios::binary),epochs(out+"/epochs.csv");epochs<<"index,kind,round,mode,slot,src,dst,steps,region,policy,record_offset,record_count,event_us\n";
 size_t offset=0;int lastpolicy=-1;
 // Buffering changes no intra-kernel work. Batches synchronize at <=128 launches.
 for(size_t i=0;i<plan.size();){size_t end=std::min(i+chunk,plan.size());if(plan[i].kind==3)end=i+1;
  ck(cuMemsetD8Async(records,0,(end-i)*28*sizeof(Record),stream),"clear records");
  for(size_t j=i;j<end;j++){auto q=plan[j];if(q.kind==3){if(q.policy!=lastpolicy){ck(cuMemcpyHtoDAsync(mapping,maps.at(q.policy).data(),512*4,stream),"mapping");lastpolicy=q.policy;}ck(cuEventRecord(e0,stream),"start");}
   launch(q,records+(j-i)*28*sizeof(Record));if(q.kind==3)ck(cuEventRecord(e1,stream),"end");
  }
  ck(cuStreamSynchronize(stream),"batch ready");std::vector<Record>r((end-i)*28);ck(cuMemcpyDtoH(r.data(),records,r.size()*sizeof(Record)),"download");
  // Preserve one exact downloaded batch before validation, once per batch.
  {std::ofstream last(out+"/last_downloaded_batch.bin",std::ios::binary);last.write((char*)r.data(),r.size()*sizeof(Record));}
  for(size_t j=i;j<end;j++){auto q=plan[j];auto*rr=r.data()+(j-i)*28;std::set<unsigned>observed(rr->roster_begin,rr->roster_begin+NSM);if(observed!=ids)throw std::runtime_error("Missing/duplicate SM in measured launch");for(int k=0;k<NSM;k++)if(rr->roster_begin[k]!=rr->roster_end[k])throw std::runtime_error("SM migration");int n=q.kind==3?28:1;float elapsed=0;if(q.kind==3)ck(cuEventElapsedTime(&elapsed,e0,e1),"elapsed");
   for(int k=0;k<n;k++){auto&v=rr[k];if(v.errors||v.src_begin!=v.src_end||(q.kind!=2&&v.dst_begin!=v.dst_end))throw std::runtime_error("Kernel error or migration");if(q.kind==2){if(v.src_begin!=unsigned(q.src)||v.src_value!=first[q.region])throw std::runtime_error("Chase check");}else{if(v.src_value!=unsigned(q.steps+16)||v.dst_value!=unsigned(q.steps+16))throw std::runtime_error("Handshake count");if(q.kind==1&&(v.src_begin!=unsigned(q.src)||v.dst_begin!=unsigned(q.dst)))throw std::runtime_error("Wrong pair");if(q.kind==3){const auto&m=maps.at(q.policy);if(m.at(v.src_begin*2)!=k||m.at(v.src_begin*2+1)!=0||m.at(v.dst_begin*2)!=k||m.at(v.dst_begin*2+1)!=1)throw std::runtime_error("Wrong concurrent pair mapping");}}if(!v.ns||!v.cycles)throw std::runtime_error("No timing");}
   raw.write((char*)rr,n*sizeof(Record));epochs<<j<<','<<q.kind<<','<<q.round<<','<<q.mode<<','<<q.slot<<','<<q.src<<','<<q.dst<<','<<q.steps<<','<<q.region<<','<<q.policy<<','<<offset<<','<<n<<','<<elapsed*1000<<'\n';offset+=n;
  }raw.flush();epochs.flush();i=end;if(i%4096==0||i==plan.size())std::cout<<"COMPLETED "<<i<<'/'<<plan.size()<<std::endl;
 }
 std::ofstream ok(out+"/correctness.json");ok<<"{\"status\":\"PASS\",\"launches\":"<<plan.size()<<",\"records\":"<<offset<<",\"wall_seconds\":"<<std::chrono::duration<double>(Clock::now()-begin).count()<<"}\n";
 cuEventDestroy(e0);cuEventDestroy(e1);cuStreamDestroy(stream);cuMemFree(mapping);cuMemFree(records);cuMemFree(starts);cuMemFree(chain);cuMemFree(flags);cuModuleUnload(mod);cuDevicePrimaryCtxRelease(dev);return 0;
}catch(std::exception&e){std::cerr<<e.what()<<std::endl;return 2;}}
