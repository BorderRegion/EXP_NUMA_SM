#include "driver_backend.hpp"
#include "probe_types.hpp"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iomanip>
#include <map>
#include <random>
#include <numeric>
#include <algorithm>
#include <set>
#include <array>
#include <cmath>
#include <cstring>
static unsigned physical(unsigned r,unsigned k,unsigned w){return ((k/w)*64+r)*w+k%w;}
static unsigned parity(unsigned r){return __builtin_popcount(r)&1;}
int main(int argc,char**argv){try{
 std::map<std::string,std::string>a;for(int i=1;i+1<argc;i+=2)a[argv[i]]=argv[i+1];auto get=[&](std::string k,std::string d){return a.count(k)?a[k]:d;};
 std::string out=get("--out","."),kind=get("--kind","main");int allocation=std::stoi(get("--allocation","0")),rounds=std::stoi(get("--rounds","8"));bool small=get("--small","0")=="1";
 std::filesystem::create_directories(out);Backend b(1);int l2;ck(cuDeviceGetAttribute(&l2,CU_DEVICE_ATTRIBUTE_L2_CACHE_SIZE,b.dev),"L2");
 if(l2!=4194304||b.sms!=56||b.groups.size()!=2||b.groups[0].sms!=28||b.groups[1].sms!=28)throw std::runtime_error("Unexpected device/resource geometry; requires protocol revision");
 CUuuid uid;ck(cuDeviceGetUuid(&uid,b.dev),"UUID");
 CUmodule mod;ck(cuModuleLoad(&mod,get("--cubin","").c_str()),"module");CUfunction probe,sweep,place;ck(cuModuleGetFunction(&probe,mod,"probe"),"probe");ck(cuModuleGetFunction(&sweep,mod,"sweep"),"sweep");ck(cuModuleGetFunction(&place,mod,"parity_consume"),"place");
 Buffer data(128ull<<20),scratch(128ull<<20),scratchout(256*8),permutation(512*4),startbuf(512*4),records0(512*sizeof(ProbeRecord)),records1(512*sizeof(ProbeRecord)),sums(64*8),diag0(32*sizeof(ProbeRecord)),diag1(32*sizeof(ProbeRecord));
 ck(cuMemsetD32(scratch.p,0x5a5a5a5a,scratch.bytes/4),"scratch initialize");
 size_t free,total;ck(cuMemGetInfo(&free,&total),"headroom");if(free<std::max(size_t(2ull<<30),total*15/100))throw std::runtime_error("memory headroom");
 CUevent fork,joined;ck(cuEventCreate(&fork,0),"fork event");ck(cuEventCreate(&joined,0),"join event");
 std::ofstream meta(out+"/epochs.csv"),raw(out+"/records.bin",std::ios::binary),foot(out+"/footprints.csv"),perms(out+"/permutations.bin",std::ios::binary),cross(out+"/cross.csv"),fit(out+"/fits.csv");
 meta<<"epoch,allocation,kind,bytes,window_bytes,cg,concurrent,mode,repeats,cache,round,group_order,group,cpu_ready_ms,parent_event_ms,group_event_ms,raw_record_offset,records,unique_chain_words,chain_prefix_loads\n";
 meta<<std::setprecision(12);cross<<std::setprecision(12);fit<<std::setprecision(12);
 foot<<"bytes,window_bytes,regions,region_words,unique_full_words,full_replicas,latency_prefix_per_replica,allocation_base,scratch_bytes,fit_regions\n";
 fit<<"bytes,window_bytes,mask,bias,train_score,train_log_advantage,spatial_holdout_log_advantage,late_all_log_advantage,fit_rounds,fit_regions\n";
 cross<<"bytes,window_bytes,round,cache,cg,mask,bias,kind,layout_swap,compute_swap,group,data_class,cpu_ready_ms,parent_event_ms,group_event_ms,checksum_pass,sm_set\n";
 uint64_t epoch=0,offset=0;std::set<unsigned>roster[2];std::vector<unsigned>sizes=small?std::vector<unsigned>{2097152}:std::vector<unsigned>{2097152,8388608,33554432,134217728};
 if(kind=="scout")sizes={134217728};
 auto prep=[&](int cache,unsigned words){
  if(cache==0)return;
  int g=cache==1?0:1;CUdeviceptr pointer=cache==3?scratch.p:data.p;unsigned n=cache==3?scratch.bytes/4:words;
  if(cache==3){ck(cuCtxSetCurrent(b.primary),"evict current");void*args[]={&pointer,&n,&scratchout.p};ck(cuLaunchKernel(sweep,256,1,1,128,1,1,0,nullptr,args,nullptr),"eviction intervention");ck(cuCtxSynchronize(),"eviction ready");}
  else {b.current(g);void*args[]={&pointer,&n,&scratchout.p};ck(cuLaunchKernel(sweep,256,1,1,128,1,1,0,b.groups[g].stream,args,nullptr),"owner touch");ck(cuStreamSynchronize(b.groups[g].stream),"owner ready");}
 };
 for(unsigned bytes:sizes){for(unsigned window_bytes:(kind=="scout"?std::vector<unsigned>{128,4096,65536,2097152}:std::vector<unsigned>{4096})){
  unsigned words=bytes/4,rw=words/64,window=window_bytes/4;
  if(window>rw)throw std::runtime_error("invalid granule");
  std::vector<unsigned>host(words),starts(512),task(512),fitids(64);std::vector<uint64_t>expected(64),chain_sum(512),arithmetic_sum(512);std::vector<unsigned>chain_end(512),arithmetic_end(512);
  std::mt19937 rng(2026101603u+allocation*101u+bytes+window_bytes);
  std::set<unsigned>chain_union;
  for(unsigned r=0;r<64;r++){
   std::vector<unsigned>order(rw);std::iota(order.begin(),order.end(),0);std::shuffle(order.begin(),order.end(),rng);uint64_t sum=0;
   for(unsigned k=0;k<rw;k++){unsigned idx=physical(r,order[k],window),next=physical(r,order[(k+1)%rw],window);host[idx]=next;sum+=next;}expected[r]=sum;
   for(unsigned rep=0;rep<8;rep++){unsigned q=r*8+rep;starts[q]=physical(r,order[rep*rw/8],window);unsigned index=starts[q],arith=index;uint64_t cs=0,as=0;
    for(int n=0;n<256;n++){chain_union.insert(index);index=host[index];cs+=index;arith=arith*1664525u+1013904223u;as+=arith;}chain_sum[q]=cs;chain_end[q]=index;arithmetic_sum[q]=as;arithmetic_end[q]=arith;
   }
  }
  ck(cuCtxSetCurrent(b.primary),"upload current");ck(cuMemcpyHtoD(data.p,host.data(),bytes),"upload data");startbuf.upload(starts.data());
  std::iota(fitids.begin(),fitids.end(),0);std::mt19937 fr(2026101607);std::shuffle(fitids.begin(),fitids.end(),fr);std::array<bool,64>isfit{};for(int j=0;j<32;j++)isfit[fitids[j]]=true;
  std::string fitlist;for(int j=0;j<32;j++)fitlist+=(j?";":"")+std::to_string(fitids[j]);
  foot<<bytes<<','<<window_bytes<<",64,"<<rw<<','<<words<<",8,256,"<<data.p<<','<<scratch.bytes<<','<<fitlist<<'\n';foot.flush();
  std::array<double,64>train{},late{};std::array<unsigned,64>ntrain{},nlate{};
  std::vector<int>modes=kind=="scout"?std::vector<int>{0,4}:std::vector<int>{0,1,2,3,4,5};
  if(small)modes={0,1,2,3,4,5};
  for(int round=0;round<rounds;round++){
   std::iota(task.begin(),task.end(),0);std::mt19937 tr(2026101611u+round*7919u);std::shuffle(task.begin(),task.end(),tr);ck(cuCtxSetCurrent(b.primary),"permutation current");permutation.upload(task.data());perms.write((char*)task.data(),task.size()*4);
   // Four crossed cache states. Each recipe/order is frozen, not chosen by speed.
   for(int cache:std::vector<int>{0,1,2,3})for(int concurrent=0;concurrent<2;concurrent++)for(int cg=0;cg<2;cg++)for(int mode:modes){
    int repeats=mode==2||mode==3?4:1;unsigned base=0,grid=concurrent?512:8;int first=(round+cache+cg+mode)%2,second=1-first;
    auto launch=[&](int g){b.current(g);CUdeviceptr rp=g?records1.p:records0.p;void*args[]={&data.p,&permutation.p,&startbuf.p,&rp,&rw,&window,&base,&mode,&cg,&repeats};ck(cuEventRecord(b.groups[g].start,b.groups[g].stream),"group start");ck(cuLaunchKernel(probe,grid,1,1,128,1,1,0,b.groups[g].stream,args,nullptr),"probe launch");ck(cuEventRecord(b.groups[g].end,b.groups[g].stream),"group end");};
    // Natural steady warmup is identical work before the measured launch.
    if(cache==0){for(int g:{first,second})launch(g);b.join();}
    prep(cache,words);
    ck(cuCtxSetCurrent(b.primary),"fork current");auto begin=Clock::now();ck(cuEventRecord(fork,nullptr),"fork record");
    for(int g:{first,second}){if(!concurrent&&cache!=0)prep(cache,words);b.current(g);ck(cuStreamWaitEvent(b.groups[g].stream,fork,0),"fork wait");launch(g);if(!concurrent)ck(cuStreamSynchronize(b.groups[g].stream),"sparse isolated ready");}
    ck(cuCtxSetCurrent(b.primary),"join current");for(int g:{first,second})ck(cuStreamWaitEvent(nullptr,b.groups[g].end,0),"parent join");ck(cuEventRecord(joined,nullptr),"parent end");ck(cuEventSynchronize(joined),"parent output ready");double cpu=ms(begin,Clock::now());float overall;ck(cuEventElapsedTime(&overall,fork,joined),"parent event span");
    std::array<std::array<double,64>,2>logs{};
    for(int g=0;g<2;g++){
     std::vector<ProbeRecord>rec(512);(g?records1:records0).download(rec.data());float event_ms;ck(cuEventElapsedTime(&event_ms,b.groups[g].start,b.groups[g].end),"group event span");
     if(event_ms>5000)throw std::runtime_error("finite probe exceeds 5 seconds; stop before expanding");
     for(unsigned pos=0;pos<512;pos++){
      auto &v=rec[pos];unsigned q=task[pos],region=q/8;
      if(v.region!=region||v.logical_position!=pos||v.sm_begin!=v.sm_end||v.ticks==0)throw std::runtime_error("invalid execution record");
      uint64_t sum=mode==4?chain_sum[q]:mode==5?arithmetic_sum[q]:expected[region]*repeats;
      if(v.sum!=sum)throw std::runtime_error("full checksum mismatch");
      if(mode>=4&&(v.first!=starts[q]||v.last!=(mode==4?chain_end[q]:arithmetic_end[q])))throw std::runtime_error("dependency endpoint mismatch");
      roster[g].insert(v.sm_begin);logs[g][region]+=std::log(double(v.ticks))/8;
     }
     raw.write((char*)rec.data(),rec.size()*sizeof(ProbeRecord));
     meta<<epoch<<','<<allocation<<','<<kind<<','<<bytes<<','<<window_bytes<<','<<cg<<','<<concurrent<<','<<mode<<','<<repeats<<','<<cache<<','<<round<<','<<first<<','<<g<<','<<cpu<<','<<overall<<','<<event_ms<<','<<offset<<",512,"<<(mode==4?chain_union.size():0)<<','<<(mode==4?512*256:0)<<'\n';offset+=512;
    }
    // Model family is frozen. Fit only first four rounds and 32 spatial regions,
    // natural steady, simultaneous, cg, full coalesced one-pass. All other
    // conditions and last four rounds are untouched confirmation diagnostics.
    if(cache==0&&concurrent==1&&cg==1&&mode==0){double mean=0;std::array<double,64>d{};for(int r=0;r<64;r++){d[r]=logs[1][r]-logs[0][r];mean+=d[r]/64;}
     for(int r=0;r<64;r++){if(round<4){train[r]+=d[r]-mean;ntrain[r]++;}else{late[r]+=d[r]-mean;nlate[r]++;}}
    }
    epoch++;meta.flush();
   }
   std::cout<<"ROUND_COMPLETE allocation="<<allocation<<" bytes="<<bytes<<" window="<<window_bytes<<" round="<<round<<" epochs="<<epoch<<std::endl;
  }
  // Exact parity family, <=6 selector bits. No physical-domain inference.
  unsigned mask=1,bias=0;double best=-1;
  for(unsigned m=1;m<64;m++){double score=0;for(int r=0;r<64;r++)if(isfit[r])score+=(parity(r&m)?-1:1)*train[r]/std::max(1u,ntrain[r])/32;
   if(std::abs(score)>best){best=std::abs(score);mask=m;bias=score<0;}
  }
  double train_score=0,hold_score=0,late_score=0;
  for(int r=0;r<64;r++){double sign=(parity(r&mask)^bias)?-1:1;if(isfit[r])train_score+=sign*train[r]/std::max(1u,ntrain[r])/32;else hold_score+=sign*train[r]/std::max(1u,ntrain[r])/32;late_score+=sign*late[r]/std::max(1u,nlate[r])/64;}
  fit<<bytes<<','<<window_bytes<<','<<mask<<','<<bias<<','<<best<<','<<train_score<<','<<hold_score<<','<<late_score<<",0:3,"<<fitlist<<'\n';fit.flush();
  // A finite actual cross on the still-live allocation, not a predicted speed gate.
  // Two data layouts swap paired regions by the lowest selected address bit.
  // Each whole-pool run consumes every logical region once (no data replication).
  if(kind=="main"){
   unsigned flip=mask&-mask;std::vector<unsigned>swapped(words);
   for(unsigned r=0;r<64;r++)for(unsigned k=0;k<rw;k++)swapped[physical(r,k,window)]=host[physical(r^flip,k,window)];
   for(int round=0;round<(small?2:8);round++)for(int layout_rank=0;layout_rank<2;layout_rank++){
    int layout_swap=layout_rank^((round+allocation)&1);
    ck(cuCtxSetCurrent(b.primary),"layout current");ck(cuMemcpyHtoD(data.p,layout_swap?swapped.data():host.data(),bytes),"one stored layout upload");unsigned logical_xor=layout_swap?flip:0;
    for(int cache=0;cache<4;cache++){
     std::vector<int>cells{0,1,2,3,4,5};std::rotate(cells.begin(),cells.begin()+(round%6),cells.end());if(round&1)std::reverse(cells.begin(),cells.end());
     for(int cell:cells){int cg=1,repeats=1,compute_swap=cell>=4?cell-4:0;bool joint=cell>=4;int single_group=cell/2,single_class=cell%2;int first=round%2;prep(cache,words);
      auto launch=[&](int g,unsigned d){b.current(g);CUdeviceptr dp=g?diag1.p:diag0.p;void*args[]={&data.p,&sums.p,&dp,&rw,&window,&mask,&bias,&d,&logical_xor,&cg,&repeats};ck(cuEventRecord(b.groups[g].start,b.groups[g].stream),"cross start");ck(cuLaunchKernel(place,32,1,1,128,1,1,0,b.groups[g].stream,args,nullptr),"cross launch");ck(cuEventRecord(b.groups[g].end,b.groups[g].stream),"cross end");};
      // Natural steady warmup on the exact path, outside the measured span.
      if(cache==0){if(joint){for(int g:{first,1-first})launch(g,g^compute_swap);}else launch(single_group,single_class);b.join();}
      ck(cuCtxSetCurrent(b.primary),"cross fork");auto begin=Clock::now();ck(cuEventRecord(fork,nullptr),"cross fork record");
      std::vector<int>active=joint?std::vector<int>{first,1-first}:std::vector<int>{single_group};
      for(int g:active){b.current(g);ck(cuStreamWaitEvent(b.groups[g].stream,fork,0),"cross wait");launch(g,joint?g^compute_swap:single_class);}
      ck(cuCtxSetCurrent(b.primary),"cross join");for(int g:active)ck(cuStreamWaitEvent(nullptr,b.groups[g].end,0),"cross parent wait");ck(cuEventRecord(joined,nullptr),"cross parent end");ck(cuEventSynchronize(joined),"cross ready");double cpu=ms(begin,Clock::now());float overall;ck(cuEventElapsedTime(&overall,fork,joined),"cross event");
      std::vector<uint64_t>got(64);sums.download(got.data());
      for(int g:active){std::vector<ProbeRecord>d(32);(g?diag1:diag0).download(d.data());std::set<unsigned>sm;
       for(auto&v:d){if(v.sm_begin!=v.sm_end||v.sum!=expected[v.region^logical_xor]||got[v.region^logical_xor]!=v.sum)throw std::runtime_error("cross full-output/position mismatch");sm.insert(v.sm_begin);}
       float ge;ck(cuEventElapsedTime(&ge,b.groups[g].start,b.groups[g].end),"cross group time");std::string sms;for(auto s:sm)sms+=(sms.empty()?"":";")+std::to_string(s);
       cross<<bytes<<','<<window_bytes<<','<<round<<','<<cache<<','<<cg<<','<<mask<<','<<bias<<','<<(joint?"JOINT":"CELL")<<','<<layout_swap<<','<<compute_swap<<','<<g<<','<<(joint?g^compute_swap:single_class)<<','<<cpu<<','<<overall<<','<<ge<<",1,"<<sms<<'\n';
      }
     }
     cross.flush();
    }
   }
  }
 }}
 for(int g=0;g<2;g++)for(unsigned sm:roster[g])if(roster[1-g].count(sm))throw std::runtime_error("Green resource rosters overlap");
 std::ofstream result(out+"/correctness.json");result<<"{\"status\":\"PASS\",\"epochs\":"<<epoch<<",\"record_bytes\":"<<sizeof(ProbeRecord)<<",\"records\":"<<offset<<",\"unique_sm_counts\":["<<roster[0].size()<<','<<roster[1].size()<<"],\"actual_group_sms\":[";
 for(int g=0;g<2;g++){if(g)result<<',';result<<'[';bool comma=false;for(auto sm:roster[g]){if(comma)result<<',';result<<sm;comma=true;}result<<']';}result<<"],\"all_full_consumer_checksums\":true,\"dependent_prefix_endpoints\":true,\"recorded_prefix_not_full_latency_workset\":true,\"physical_home_assumed\":false}\n";
 cuEventDestroy(fork);cuEventDestroy(joined);cuModuleUnload(mod);return 0;
}catch(std::exception&e){std::cerr<<e.what()<<'\n';return 2;}}
