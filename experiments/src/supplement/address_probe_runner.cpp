#include "driver_backend.hpp"
#include "address_common.hpp"
#include <fstream>
#include <iostream>
#include <filesystem>
#include <map>
#include <random>
#include <numeric>
#include <algorithm>
#include <set>
#include <memory>
static unsigned physical(unsigned r,unsigned off,unsigned regions,unsigned window){return ((off/window)*regions+r)*window+off%window;}
int main(int argc,char**argv){try{
 std::map<std::string,std::string>a;for(int i=1;i+1<argc;i+=2)a[argv[i]]=argv[i+1];auto get=[&](std::string k,std::string d){return a.count(k)?a[k]:d;};std::string out=get("--out","."),mode=get("--mode","dev");int allocation=std::stoi(get("--allocation","0")),rounds=std::stoi(get("--rounds","6"));bool small=get("--qualify","0")=="1";
 std::filesystem::create_directories(out);Backend b(1);int l2;ck(cuDeviceGetAttribute(&l2,CU_DEVICE_ATTRIBUTE_L2_CACHE_SIZE,b.dev),"L2 query");if(l2!=4194304||b.sms!=56||b.groups.size()!=2||b.groups[0].sms!=28||b.groups[1].sms!=28)throw std::runtime_error("actual device differs from registered T10 protocol");
 CUmodule mod;ck(cuModuleLoad(&mod,get("--cubin","").c_str()),"probe module");CUfunction kernel,prep;ck(cuModuleGetFunction(&kernel,mod,"address_probe"),"probe function");ck(cuModuleGetFunction(&prep,mod,"prepare_input"),"prepare function");Buffer data(32ull<<20),scratch(256*8);
 std::ofstream aggregate(out+"/observations.csv"),epochs(out+"/epochs.csv"),footprint(out+"/footprints.csv");aggregate<<"bytes,recipe,access,window_bytes,round,group,region,sm,segments,loads,total_ticks,min_ticks,max_ticks\n";epochs<<"bytes,recipe,access,window_bytes,round,cpu_ready_ms,group0_ms,group1_ms,max_segment_ms,coverage_sm\n";footprint<<"bytes,window_bytes,regions,words,virtual_sectors32,virtual_lines128,per_region_words,segment_words,segments,replicas,explicit_device_bytes\n";
 for(unsigned bytes:{524288u,4194304u,33554432u}){if(small&&bytes!=524288)continue;unsigned words=bytes/4;
 for(int cg=0;cg<2;cg++)for(int throughput=0;throughput<2;throughput++){
 for(int round=0;round<rounds;round++){unsigned window_bytes=mode=="dev"?(round%2?65536:4096):unsigned(std::stoul(get("--window-bytes","4096")));unsigned window=window_bytes/4,regions=std::min(32u,words/window),region_words=words/regions,segment_words=small?64:1024,segments=region_words/segment_words,ctas=regions*8;
  std::vector<unsigned> host(words),starts(ctas),expected(regions);std::mt19937 rng(2026101503u+allocation*101+window_bytes+bytes);
  for(unsigned r=0;r<regions;r++){std::vector<unsigned>order(region_words);std::iota(order.begin(),order.end(),0);std::shuffle(order.begin(),order.end(),rng);unsigned sum=0;for(unsigned k=0;k<region_words;k++){unsigned idx=physical(r,order[k],regions,window),next=physical(r,order[(k+1)%region_words],regions,window);host[idx]=next;sum+=idx;}expected[r]=sum;for(unsigned rep=0;rep<8;rep++)starts[r*8+rep]=physical(r,order[rep*region_words/8],regions,window);}
  ck(cuCtxSetCurrent(b.primary),"input primary");ck(cuMemcpyHtoD(data.p,host.data(),bytes),"input upload");std::vector<unsigned> task_permutation(ctas);std::iota(task_permutation.begin(),task_permutation.end(),0);std::mt19937 task_rng(2026101503u+round*17u);std::shuffle(task_permutation.begin(),task_permutation.end(),task_rng);Buffer task_map(ctas*4);task_map.upload(task_permutation.data());std::ofstream task_order(out+"/task_order_"+std::to_string(bytes)+"_"+std::to_string(window_bytes)+"_"+std::to_string(round)+".txt");for(auto t:task_permutation)task_order<<t<<'\n';
  std::vector<ProbeState>initial(ctas);for(unsigned i=0;i<ctas;i++)initial[i]={starts[i],0};
  std::unique_ptr<Buffer>state[2],record[2];size_t rec_bytes=size_t(ctas)*segments*sizeof(ProbeRecord);for(int g=0;g<2;g++){state[g].reset(new Buffer(ctas*sizeof(ProbeState)));record[g].reset(new Buffer(rec_bytes));state[g]->upload(initial.data());}
  size_t free,total;ck(cuMemGetInfo(&free,&total),"headroom");if(free<std::max(size_t(2ull<<30),total*15/100)||data.bytes+scratch.bytes+task_map.bytes+2*(ctas*sizeof(ProbeState)+rec_bytes)>256ull<<20)throw std::runtime_error("probe memory bounds");
  if(round==0||mode=="dev"&&round==1)footprint<<bytes<<','<<window_bytes<<','<<regions<<','<<words<<','<<bytes/32<<','<<bytes/128<<','<<region_words<<','<<segment_words<<','<<segments<<",8,"<<data.bytes+scratch.bytes+task_map.bytes+2*(ctas*sizeof(ProbeState)+rec_bytes)<<'\n';
  auto prepare=[&](){ck(cuCtxSetCurrent(b.primary),"prepare primary");void*args[]={&data.p,&words,&scratch.p};ck(cuLaunchKernel(prep,256,1,1,128,1,1,0,nullptr,args,nullptr),"warming traversal");ck(cuCtxSynchronize(),"warming ready");};
  auto launch=[&](int g,unsigned seg){b.current(g);void*args[]={&data.p,&task_map.p,&state[g]->p,&record[g]->p,&regions,&window,&seg,&segment_words,&cg,&throughput};ck(cuEventRecord(b.groups[g].start,b.groups[g].stream),"segment start");ck(cuLaunchKernel(kernel,ctas,1,1,128,1,1,0,b.groups[g].stream,args,nullptr),"probe segment");ck(cuEventRecord(b.groups[g].end,b.groups[g].stream),"segment end");};
  float max_segment=0;double gt[2]={0,0};auto check_segment=[&](int g){float t;ck(cuEventElapsedTime(&t,b.groups[g].start,b.groups[g].end),"segment elapsed");max_segment=std::max(max_segment,t);gt[g]+=t;if(t>20)throw std::runtime_error("probe segment >20ms safety bound");};
  int order[2]={round%2,1-round%2};auto begin=Clock::now();
  if(throughput){prepare();for(unsigned seg=0;seg<segments;seg++){for(int g:order)launch(g,seg);b.join();for(int g:order)check_segment(g);}}
  else for(int g:order){prepare();for(unsigned seg=0;seg<segments;seg++){launch(g,seg);ck(cuStreamSynchronize(b.groups[g].stream),"latency ready");check_segment(g);}}
  double cpu=ms(begin,Clock::now());ck(cuCtxSetCurrent(b.primary),"read primary");std::set<unsigned>sms;
  for(int g=0;g<2;g++){std::vector<ProbeState>st(ctas);state[g]->download(st.data());for(unsigned i=0;i<ctas;i++)if(st[i].sum!=expected[i/8]||(!throughput&&st[i].index!=starts[i]))throw std::runtime_error("full probe sum/chain closure mismatch");std::vector<ProbeRecord>raw(ctas*segments);record[g]->download(raw.data());std::string key=std::to_string(bytes)+"_"+std::to_string(cg)+"_"+std::to_string(throughput)+"_"+std::to_string(window_bytes)+"_"+std::to_string(round)+"_"+std::to_string(g);std::ofstream bin(out+"/segments_"+key+".bin",std::ios::binary);bin.write((char*)raw.data(),rec_bytes);
   struct A{uint64_t n=0,loads=0,ticks=0,mn=~0ull,mx=0;};std::map<std::pair<unsigned,unsigned>,A>agg;for(unsigned seg=0;seg<segments;seg++)for(unsigned q=0;q<ctas;q++){auto&v=raw[seg*ctas+q];if(v.sm_begin!=v.sm_end||v.loads!=segment_words)throw std::runtime_error("segment observation invalid");if(!throughput){unsigned previous=seg?raw[(seg-1)*ctas+q].last:starts[q];if(v.first!=previous)throw std::runtime_error("chain segment not continued");}sms.insert(v.sm_begin);auto&x=agg[{q/8,v.sm_begin}];x.n++;x.loads+=v.loads;x.ticks+=v.ticks;x.mn=std::min(x.mn,v.ticks);x.mx=std::max(x.mx,v.ticks);}
   for(auto&kv:agg){auto&x=kv.second;aggregate<<bytes<<','<<cg<<','<<throughput<<','<<window_bytes<<','<<round<<','<<g<<','<<kv.first.first<<','<<kv.first.second<<','<<x.n<<','<<x.loads<<','<<x.ticks<<','<<x.mn<<','<<x.mx<<'\n';}
  }
  epochs<<bytes<<','<<cg<<','<<throughput<<','<<window_bytes<<','<<round<<','<<cpu<<','<<gt[0]<<','<<gt[1]<<','<<max_segment<<','<<sms.size()<<'\n';epochs.flush();aggregate.flush();
 }
 std::cout<<"CONFIG_COMPLETE bytes="<<bytes<<" cg="<<cg<<" throughput="<<throughput<<std::endl;
 }}
 std::ofstream(out+"/correctness.json")<<"{\"status\":\"PASS\",\"chain_closed\":true,\"full_CPU_uint32_sums\":true,\"segment_state_continuation\":true}\n";cuModuleUnload(mod);return 0;
}catch(std::exception&e){std::cerr<<e.what()<<'\n';return 2;}}
