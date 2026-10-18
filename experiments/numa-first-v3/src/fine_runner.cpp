// Post-hoc finer public-control diagnosis. Not a change to P1 confirmation.
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
struct Fine {
 CUdevice dev;CUcontext primary;std::vector<Group> groups;std::vector<CUdevResource> resources;
 Fine(){ck(cuInit(0),"init");ck(cuDeviceGet(&dev,0),"device");ck(cuDevicePrimaryCtxRetain(&primary,dev),"retain");ck(cuCtxSetCurrent(primary),"current");CUdevResource all{},rem{};ck(cuDeviceGetDevResource(dev,&all,CU_DEV_RESOURCE_TYPE_SM),"resources");unsigned n=0;ck(cuDevSmResourceSplitByCount(nullptr,&n,&all,nullptr,0,2),"simulate split");if(n!=28)throw std::runtime_error("Expected 28 symmetric 2-SM resources");std::vector<CUdevResource>rs(n);ck(cuDevSmResourceSplitByCount(rs.data(),&n,&all,&rem,0,2),"split");resources=rs;for(auto&r:rs){Group g;CUdevResourceDesc d;ck(cuDevResourceGenerateDesc(&d,&r,1),"descriptor");ck(cuGreenCtxCreate(&g.green,d,dev,CU_GREEN_CTX_DEFAULT_STREAM),"green");ck(cuCtxFromGreenCtx(&g.ctx,g.green),"context");g.sms=r.sm.smCount;ck(cuCtxSetCurrent(g.ctx),"current");ck(cuGreenCtxStreamCreate(&g.stream,g.green,CU_STREAM_NON_BLOCKING,0),"stream");ck(cuEventCreate(&g.start,0),"event");ck(cuEventCreate(&g.end,0),"event");groups.push_back(g);}ck(cuCtxSetCurrent(primary),"current");}
 int merge(const std::vector<int>&ids){std::vector<CUdevResource>rs;for(int id:ids)rs.push_back(resources.at(id));Group g;CUdevResourceDesc d;ck(cuDevResourceGenerateDesc(&d,rs.data(),rs.size()),"merged descriptor");ck(cuGreenCtxCreate(&g.green,d,dev,CU_GREEN_CTX_DEFAULT_STREAM),"merged context");ck(cuCtxFromGreenCtx(&g.ctx,g.green),"merged convert");g.sms=ids.size()*2;ck(cuCtxSetCurrent(g.ctx),"merged current");ck(cuGreenCtxStreamCreate(&g.stream,g.green,CU_STREAM_NON_BLOCKING,0),"merged stream");ck(cuEventCreate(&g.start,0),"merged start");ck(cuEventCreate(&g.end,0),"merged end");groups.push_back(g);return groups.size()-1;}
 void current(int g){ck(cuCtxSetCurrent(groups.at(g).ctx),"current");}
 ~Fine(){for(auto&g:groups){cuCtxSetCurrent(g.ctx);cuEventDestroy(g.start);cuEventDestroy(g.end);cuStreamDestroy(g.stream);cuCtxSetCurrent(primary);cuGreenCtxDestroy(g.green);}cuDevicePrimaryCtxRelease(dev);}
};
unsigned physical(unsigned r,unsigned k){return ((k/1024)*64+r)*1024+k%1024;}
unsigned par(unsigned r){return __builtin_popcount(r)&1;}
unsigned value(unsigned r,unsigned k){unsigned x=k+0x9e3779b9u*(r+1);x^=x>>16;x*=0x85ebca6bu;x^=x>>13;return x;}
int main(int argc,char**argv){try{
 std::map<std::string,std::string>a;for(int i=1;i+1<argc;i+=2)a[argv[i]]=argv[i+1];int allocation=std::stoi(a.at("--allocation"));bool qual=a.count("--qualification");std::string out=a.at("--out");std::filesystem::create_directories(out);Fine b;CUmodule mod;ck(cuModuleLoad(&mod,a.at("--cubin").c_str()),"module");CUfunction probe,sweep,place;ck(cuModuleGetFunction(&probe,mod,"probe"),"probe");ck(cuModuleGetFunction(&sweep,mod,"sweep"),"sweep");ck(cuModuleGetFunction(&place,mod,"parity_consume"),"place");
 Buffer data(32ull<<20),scratch(128ull<<20),scratchout(256*8),perm(512*4),starts(512*4),records(512*sizeof(ProbeRecord)),sums(64*8),diag0(32*sizeof(ProbeRecord)),diag1(32*sizeof(ProbeRecord));ck(cuMemsetD32(scratch.p,0x5a5a5a5a,scratch.bytes/4),"scratch");size_t free,total;ck(cuMemGetInfo(&free,&total),"memory");if(free<std::max(size_t(2ull<<30),total*15/100))throw std::runtime_error("headroom");
 std::ofstream meta(out+"/epochs.csv"),raw(out+"/records.bin",std::ios::binary),cross(out+"/cross.csv"),fits(out+"/fits.csv");meta<<std::setprecision(12);cross<<std::setprecision(12);fits<<std::setprecision(12);
 meta<<"bytes,round,content_xor,cache,cg,mode,group,group_order_rank,event_ms,cpu_ready_ms,raw_record_offset,records\n";cross<<"bytes,control_scope,round,cache,mode,layout_swap,compute_swap,kind,group,data_class,event_ms,group_event_ms,cpu_ready_ms,checksum_pass\n";fits<<"bytes,control_scope,group0,group1,mask,bias,train_log_interaction,spatial_holdout_log_interaction,late_log_interaction\n";
 uint64_t offset=0;std::vector<std::set<unsigned>>rosters(28);CUevent fork,end;ck(cuEventCreate(&fork,0),"fork");ck(cuEventCreate(&end,0),"end");
 auto prep=[&](int cache,unsigned words,int owner0,int owner1){if(!cache)return;CUdeviceptr p=cache==3?scratch.p:data.p;unsigned n=cache==3?scratch.bytes/4:words;CUstream stream=nullptr;if(cache==3)ck(cuCtxSetCurrent(b.primary),"scratch context");else{int g=cache==1?owner0:owner1;b.current(g);stream=b.groups[g].stream;}void*args[]={&p,&n,&scratchout.p};ck(cuLaunchKernel(sweep,256,1,1,128,1,1,0,stream,args,nullptr),"prep");ck(cuStreamSynchronize(stream),"prep ready");};
 for(unsigned bytes:(qual?std::vector<unsigned>{2097152}:std::vector<unsigned>{2097152,33554432})){
  unsigned words=bytes/4,rw=words/64,window=1024,base=0;std::vector<unsigned>host(words),tasks(512),regions(64);std::array<uint64_t,64>expected{};std::array<std::array<double,64>,28>early{},late{};int rounds=qual?2:8;
  std::iota(regions.begin(),regions.end(),0);std::mt19937 fr(2026101617);std::shuffle(regions.begin(),regions.end(),fr);std::array<bool,64>train{};for(int i=0;i<32;i++)train[regions[i]]=true;std::ofstream fitregions(out+"/fit_regions_"+std::to_string(bytes)+".csv");fitregions<<"region,train\n";for(int rr=0;rr<64;rr++)fitregions<<rr<<','<<train[rr]<<'\n';
  for(int round=0;round<rounds;round++){
   unsigned content_xor=round&1;expected.fill(0);for(unsigned r=0;r<64;r++)for(unsigned k=0;k<rw;k++){unsigned v=value(r^content_xor,k);host[physical(r,k)]=v;expected[r]+=v;}ck(cuCtxSetCurrent(b.primary),"upload current");ck(cuMemcpyHtoD(data.p,host.data(),bytes),"upload");
   std::iota(tasks.begin(),tasks.end(),0);std::mt19937 rng(2026101699u+allocation*100003u+round*7919u);std::shuffle(tasks.begin(),tasks.end(),rng);perm.upload(tasks.data());
   for(int cache=0;cache<(qual?1:4);cache++)for(int cg=0;cg<2;cg++)for(int mode:std::vector<int>{0,2}){
    int repeats=mode==2?4:1;std::vector<int>order(28);std::iota(order.begin(),order.end(),0);std::shuffle(order.begin(),order.end(),rng);
    for(int rank=0;rank<28;rank++){int g=order[rank];unsigned grid=2;auto launch=[&](){b.current(g);void*args[]={&data.p,&perm.p,&starts.p,&records.p,&rw,&window,&base,&mode,&cg,&repeats};ck(cuEventRecord(b.groups[g].start,b.groups[g].stream),"start");ck(cuLaunchKernel(probe,grid,1,1,128,1,1,0,b.groups[g].stream,args,nullptr),"probe");ck(cuEventRecord(b.groups[g].end,b.groups[g].stream),"end");};
     if(round==0&&cache==0&&cg==0&&mode==0){grid=64;launch();ck(cuStreamSynchronize(b.groups[g].stream),"roster ready");std::vector<ProbeRecord>rr(512);records.download(rr.data());for(auto&v:rr){if(v.sm_begin!=v.sm_end||v.sum!=expected[v.region])throw std::runtime_error("roster checksum");rosters[g].insert(v.sm_begin);}grid=2;}
     if(cache==0){launch();ck(cuStreamSynchronize(b.groups[g].stream),"warm ready");}prep(cache,words,0,27);auto start=Clock::now();launch();ck(cuStreamSynchronize(b.groups[g].stream),"ready");double cpu=ms(start,Clock::now());float event;ck(cuEventElapsedTime(&event,b.groups[g].start,b.groups[g].end),"elapsed");if(event>5000)throw std::runtime_error("finite guard");std::vector<ProbeRecord>rec(512);records.download(rec.data());
     for(int pos=0;pos<512;pos++){auto&v=rec[pos];if(v.region!=tasks[pos]/8||v.logical_position!=unsigned(pos)||v.sm_begin!=v.sm_end||v.sum!=expected[v.region]*repeats)throw std::runtime_error("checksum or execution mismatch");rosters[g].insert(v.sm_begin);if(cache==0&&cg==1&&mode==0)(round<4?early:late)[g][v.region]+=std::log(double(v.ticks))/32;}
     meta<<bytes<<','<<round<<','<<content_xor<<','<<cache<<','<<cg<<','<<mode<<','<<g<<','<<rank<<','<<event<<','<<cpu<<','<<offset<<",512\n";raw.write((char*)rec.data(),rec.size()*sizeof(ProbeRecord));offset+=512;
    }
   }meta.flush();std::cout<<"FINE_ROUND "<<bytes<<' '<<round<<std::endl;
  }
  if(qual){std::vector<int>x(14),y(14);std::iota(x.begin(),x.end(),0);std::iota(y.begin(),y.end(),14);b.merge(x);b.merge(y);continue;}
  // Frozen all-pair/parity family, only natural .cg one-pass early 32 regions.
  int g0=0,g1=1;unsigned mask=1,bias=0;double best=-1;
  for(int aa=0;aa<28;aa++)for(int bb=aa+1;bb<28;bb++){double mean=0;for(int r=0;r<64;r++)if(train[r])mean+=(early[bb][r]-early[aa][r])/32;
   for(unsigned m=1;m<64;m++){double score=0;for(int r=0;r<64;r++)if(train[r])score+=(par(r&m)?-1:1)*(early[bb][r]-early[aa][r]-mean)/32;if(std::abs(score)>best){best=std::abs(score);g0=aa;g1=bb;mask=m;bias=score<0;}}
  }
  double hold=0,last=0,hm=0,lm=0;for(int r=0;r<64;r++){if(!train[r])hm+=(early[g1][r]-early[g0][r])/32;lm+=(late[g1][r]-late[g0][r])/64;}
  for(int r=0;r<64;r++){double sign=(par(r&mask)^bias)?-1:1;if(!train[r])hold+=sign*(early[g1][r]-early[g0][r]-hm)/32;last+=sign*(late[g1][r]-late[g0][r]-lm)/64;}
  fits<<bytes<<",PAIR4SM,"<<g0<<','<<g1<<','<<mask<<','<<bias<<','<<best<<','<<hold<<','<<last<<'\n';fits.flush();
  int pair0=g0,pair1=g1;unsigned pairmask=mask,pairbias=bias;
  for(int scope=0;scope<2;scope++){
  std::string scope_name=scope?"BALANCED56SM":"PAIR4SM";
  if(scope){
   double globalbest=-1;std::vector<int>bestorder;
   for(unsigned m=1;m<64;m++){std::vector<std::pair<double,int>>coeff;for(int g=0;g<28;g++){double mean=0,score=0;for(int rr=0;rr<64;rr++)if(train[rr])mean+=early[g][rr]/32;for(int rr=0;rr<64;rr++)if(train[rr])score+=(par(rr&m)?-1:1)*(early[g][rr]-mean)/32;coeff.push_back({score,g});}std::sort(coeff.begin(),coeff.end());double score=0;for(int i=0;i<14;i++)score+=(coeff[i+14].first-coeff[i].first)/14;if(score>globalbest){globalbest=score;mask=m;bestorder.clear();for(auto x:coeff)bestorder.push_back(x.second);}}
   bias=0;std::vector<int>a0(bestorder.begin(),bestorder.begin()+14),a1(bestorder.begin()+14,bestorder.end());g0=b.merge(a0);g1=b.merge(a1);rosters.resize(b.groups.size());for(int id:a0)rosters[g0].insert(rosters[id].begin(),rosters[id].end());for(int id:a1)rosters[g1].insert(rosters[id].begin(),rosters[id].end());
   double h=0,l=0,meanhold=0;for(int rr=0;rr<64;rr++)if(!train[rr])for(int i=0;i<14;i++)meanhold+=(early[a1[i]][rr]-early[a0[i]][rr])/(14*32);for(int rr=0;rr<64;rr++){double de=0,dl=0;for(int i=0;i<14;i++){de+=(early[a1[i]][rr]-early[a0[i]][rr])/14;dl+=(late[a1[i]][rr]-late[a0[i]][rr])/14;}double sign=par(rr&mask)?-1:1;if(!train[rr])h+=sign*(de-meanhold)/32;l+=sign*dl/64;}fits<<bytes<<",BALANCED56SM,"<<g0<<','<<g1<<','<<mask<<','<<bias<<','<<globalbest<<','<<h<<','<<l<<'\n';fits.flush();
   std::ofstream membership(out+"/merged_"+std::to_string(bytes)+".csv");membership<<"merged_group,fine_group,sm\n";for(int c=0;c<2;c++)for(int id:(c?a1:a0))for(unsigned sm:rosters[id])membership<<(c?g1:g0)<<','<<id<<','<<sm<<'\n';
  }else{g0=pair0;g1=pair1;mask=pairmask;bias=pairbias;}
  unsigned flip=mask&-mask;
  for(int round=0;round<8;round++)for(int rank=0;rank<2;rank++){
   int layout=rank^((round+allocation)&1);unsigned lx=layout?flip:0;expected.fill(0);for(unsigned r=0;r<64;r++)for(unsigned k=0;k<rw;k++){unsigned v=value(r^lx,k);host[physical(r,k)]=v;expected[r^lx]+=v;}ck(cuCtxSetCurrent(b.primary),"upload current");ck(cuMemcpyHtoD(data.p,host.data(),bytes),"layout upload");
   for(int cache=0;cache<4;cache++)for(int mode:std::vector<int>{0,2}){int repeats=mode==2?4:1,cg=1;std::vector<int>order{0,1,2,3,4,5};std::rotate(order.begin(),order.begin()+round%6,order.end());if(round&1)std::reverse(order.begin(),order.end());
    for(int cell:order){bool joint=cell>=4;int cs=joint?cell-4:0;std::vector<int>active=joint?std::vector<int>{round%2,1-round%2}:std::vector<int>{cell/2};prep(cache,words,g0,g1);
     auto launch=[&](int logical,unsigned d){int g=logical?g1:g0;b.current(g);CUdeviceptr dp=logical?diag1.p:diag0.p;void*args[]={&data.p,&sums.p,&dp,&rw,&window,&mask,&bias,&d,&lx,&cg,&repeats};ck(cuEventRecord(b.groups[g].start,b.groups[g].stream),"start");ck(cuLaunchKernel(place,32,1,1,128,1,1,0,b.groups[g].stream,args,nullptr),"place");ck(cuEventRecord(b.groups[g].end,b.groups[g].stream),"end");};
     if(!cache){for(int logical:active)launch(logical,joint?logical^cs:cell%2);for(int logical:active){int g=logical?g1:g0;ck(cuStreamSynchronize(b.groups[g].stream),"warm ready");}}
     ck(cuCtxSetCurrent(b.primary),"parent");auto t=Clock::now();ck(cuEventRecord(fork,nullptr),"fork");for(int logical:active){int g=logical?g1:g0;b.current(g);ck(cuStreamWaitEvent(b.groups[g].stream,fork,0),"wait");launch(logical,joint?logical^cs:cell%2);}ck(cuCtxSetCurrent(b.primary),"parent");for(int logical:active){int g=logical?g1:g0;ck(cuStreamWaitEvent(nullptr,b.groups[g].end,0),"join");}ck(cuEventRecord(end,nullptr),"end");ck(cuEventSynchronize(end),"ready");double cpu=ms(t,Clock::now());float event;ck(cuEventElapsedTime(&event,fork,end),"elapsed");
     float ge=0;for(int logical:active){int g=logical?g1:g0;std::vector<ProbeRecord>dr(32);(logical?diag1:diag0).download(dr.data());for(auto &v:dr)if(v.sm_begin!=v.sm_end||!rosters[g].count(v.sm_begin)||v.sum!=expected[v.region^lx]*repeats)throw std::runtime_error("cross actual placement mismatch");if(!joint)ck(cuEventElapsedTime(&ge,b.groups[g].start,b.groups[g].end),"group elapsed");}std::vector<uint64_t>got(64);sums.download(got.data());for(unsigned r=0;r<64;r++){unsigned dc=par(r&mask)^bias;bool used=joint||dc==unsigned(cell%2);if(used&&got[r^lx]!=expected[r^lx]*repeats)throw std::runtime_error("cross output mismatch");}
     cross<<bytes<<','<<scope_name<<','<<round<<','<<cache<<','<<mode<<','<<layout<<','<<cs<<','<<(joint?"JOINT":"CELL")<<','<<(joint?-1:cell/2)<<','<<(joint?-1:cell%2)<<','<<event<<','<<ge<<','<<cpu<<",1\n";
    }
   }cross.flush();
  }
  }
 }
 std::set<unsigned>all;std::ofstream roster(out+"/rosters.csv");roster<<"group,configured_sms,observed_sm\n";for(int g=0;g<28;g++)for(unsigned sm:rosters[g]){if(!all.insert(sm).second)throw std::runtime_error("overlap");roster<<g<<','<<b.groups[g].sms<<','<<sm<<'\n';}std::ofstream ok(out+"/correctness.json");ok<<"{\"status\":\"PASS\",\"records\":"<<offset<<",\"groups\":28,\"observed_sms\":"<<all.size()<<",\"full_checksums\":true,\"post_hoc_refinement\":true}";cuEventDestroy(fork);cuEventDestroy(end);cuModuleUnload(mod);return 0;
}catch(std::exception&e){std::cerr<<e.what()<<'\n';return 2;}}
