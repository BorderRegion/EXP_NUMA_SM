#include "scheduler.h"
#include <vector>
#include <array>
#include <algorithm>
#include <numeric>
#include <chrono>
#include <stdexcept>
#include <cmath>
#include <climits>
ScheduleConfig schedule_config;ScheduleStats schedule_stats;cudaEvent_t stage_events[6];uint32_t *schedule_ids=nullptr,*schedule_offsets=nullptr,*schedule_counter=nullptr;int schedule_bundle_count=0;
struct Meta {uint32_t len,keys[16];};static Meta* dmeta=nullptr;static int capacity=0;static std::vector<Meta> host;static std::vector<uint32_t> ids,offsets;static bool initialized=false;
static void ck(cudaError_t e){if(e!=cudaSuccess)throw std::runtime_error(cudaGetErrorString(e));}
void schedule_init(){if(initialized)return;for(auto&e:stage_events)ck(cudaEventCreate(&e));initialized=true;cudaDeviceProp p;ck(cudaGetDeviceProperties(&p,0));schedule_config.l2=p.l2CacheSize;int occ=schedule_occupancy();schedule_config.workers=p.multiProcessorCount*std::max(1,occ);}
void schedule_times(){float* fields[]={&schedule_stats.preprocess_ms,&schedule_stats.scan_ms,&schedule_stats.sort_ms,&schedule_stats.build_ms,&schedule_stats.render_ms};for(int i=0;i<5;i++)ck(cudaEventElapsedTime(fields[i],stage_events[i],stage_events[i+1]));}
__global__ void features(int n,const uint2* ranges,const uint32_t* list,int q,Meta* m){int t=blockIdx.x*blockDim.x+threadIdx.x;if(t>=n)return;uint2 r=ranges[t];uint32_t len=r.y-r.x;m[t].len=len;for(int j=0;j<16;j++){uint32_t at=j<q/2?j:((uint64_t)(j-q/2)*(len?len-1:0))/max(1,q/2-1);uint32_t key=(j<q&&at<len)?list[r.x+at]:UINT_MAX;for(int z=0;z<j;z++)if(m[t].keys[z]==key){key=UINT_MAX;break;}m[t].keys[j]=key;}}
static uint32_t mix(uint32_t x){x^=x>>16;x*=0x7feb352d;x^=x>>15;x*=0x846ca68b;x^=x>>16;return x;}
static uint32_t morton(uint32_t x,uint32_t y){uint32_t z=0;for(int i=0;i<16;i++)z|=((x>>i)&1)<<(2*i)|((y>>i)&1)<<(2*i+1);return z;}
void schedule_prepare(int n,int gx,const uint2* ranges,const uint32_t* list){
 schedule_stats=ScheduleStats{};schedule_stats.tiles=n;
 if(schedule_config.policy==0)return;
 if(n>capacity){if(dmeta){ck(cudaFree(dmeta));ck(cudaFree(schedule_ids));ck(cudaFree(schedule_offsets));ck(cudaFree(schedule_counter));}ck(cudaMalloc(&dmeta,n*sizeof(Meta)));ck(cudaMalloc(&schedule_ids,n*4));ck(cudaMalloc(&schedule_offsets,(n+1)*4));ck(cudaMalloc(&schedule_counter,4));capacity=n;}
 int p=schedule_config.policy,q=schedule_config.q,k=schedule_config.k;
 // Identity and spatial order are invariant under changing cameras. Cache their
 // validated device tables across frames; queue claims still reset every frame.
 static int previous_policy=-1,previous_n=-1,previous_gx=-1,previous_k=-1;
 bool reuse=(p==1||p==2)&&p==previous_policy&&n==previous_n&&gx==previous_gx&&k==previous_k;
 previous_policy=p;previous_n=n;previous_gx=gx;previous_k=k;
 if(reuse){schedule_stats.bundles=schedule_bundle_count;if(schedule_config.executor==1)ck(cudaMemset(schedule_counter,0,4));return;}
 if(p>=3){features<<<(n+255)/256,256>>>(n,ranges,list,p==3?0:q,dmeta);ck(cudaGetLastError());host.resize(n);ck(cudaMemcpy(host.data(),dmeta,n*sizeof(Meta),cudaMemcpyDeviceToHost));}
 auto start=std::chrono::steady_clock::now();ids.resize(n);std::iota(ids.begin(),ids.end(),0u);offsets.clear();offsets.push_back(0);
 std::vector<Meta> feature;if(p>=3)feature=host;
 if(p>=3){for(auto&m:host)schedule_stats.list_entries+=m.len;}
 if(p==7){ // C1: fixed cyclic feature shift within comparable log-work buckets.
  std::array<std::vector<int>,32> groups;for(int i=0;i<n;i++){int b=host[i].len?31-__builtin_clz(host[i].len):0;groups[b].push_back(i);}for(auto&g:groups)for(size_t j=0;j<g.size();j++)std::copy(std::begin(host[g[(j+1)%g.size()]].keys),std::end(host[g[(j+1)%g.size()]].keys),feature[g[j]].keys);
 }
 auto sig=[&](uint32_t t){uint32_t s=UINT_MAX;for(int j=0;j<q;j++)if(feature[t].keys[j]!=UINT_MAX)s=std::min(s,mix(feature[t].keys[j]));return s;};
 std::vector<uint32_t> signatures(n);if(p>=4)for(int i=0;i<n;i++)signatures[i]=sig(i);
 if(p==2)std::stable_sort(ids.begin(),ids.end(),[&](uint32_t a,uint32_t b){return morton(a%gx,a/gx)<morton(b%gx,b/gx);});
 if(p==3)std::stable_sort(ids.begin(),ids.end(),[&](uint32_t a,uint32_t b){return host[a].len>host[b].len;});
 if(p>=4)std::stable_sort(ids.begin(),ids.end(),[&](uint32_t a,uint32_t b){return signatures[a]<signatures[b];});
 if(p==5){ // B5: ordinary resource grouping, balanced work within 16-task neighborhoods.
  for(int s=0;s<n;s+=16){int e=std::min(n,s+16);std::stable_sort(ids.begin()+s,ids.begin()+e,[&](auto a,auto b){return host[a].len>host[b].len;});std::vector<uint32_t> v(ids.begin()+s,ids.begin()+e);int groups=(e-s+k-1)/k;int at=s;for(int g=0;g<groups;g++)for(int j=g;j<e-s;j+=groups)ids[at++]=v[j];}
 }
 if(p>=6){
  std::vector<uint32_t> pending=ids,ordered;ordered.reserve(n);std::vector<bool> used(n,false);int consumed=0;
  double cap=schedule_config.alpha*schedule_config.l2/std::max(1,schedule_config.workers);double avg=schedule_stats.list_entries/double(std::max(1,n));double workcap=std::max(1.0,avg*k*2.0);
  for(int base=0;base<n;base++){if(used[base])continue;std::vector<uint32_t> keys;double footprint=0,work=0;int num=0;
   while(num<k){int best=-1;double bestScore=1e100,bestBytes=0;
    for(int j=base;j<(num?std::min(n,base+16):base+1);j++){if(used[j])continue;uint32_t id=pending[j];int valid=0,newkeys=0;for(int t=0;t<q;t++){auto key=feature[id].keys[t];if(key==UINT_MAX)continue;valid++;if(std::find(keys.begin(),keys.end(),key)==keys.end())newkeys++;}
     double fraction=valid?double(newkeys)/valid:0;double bytes=host[id].len*(4.0+36.0*fraction);double w=host[id].len;
     if(num&&((p!=8&&footprint+bytes>cap)||work+w>workcap)){schedule_stats.cap_hits++;continue;}
     double score=bytes+4*w+4*std::max(0.0,work+w-workcap);
     if(score<bestScore){best=j;bestScore=score;bestBytes=bytes;}}
    if(best<0)break;uint32_t id=pending[best];used[best]=true;consumed++;ordered.push_back(id);work+=host[id].len;footprint+=bestBytes;num++;for(int t=0;t<q;t++){auto key=feature[id].keys[t];if(key!=UINT_MAX&&std::find(keys.begin(),keys.end(),key)==keys.end())keys.push_back(key);}
   }
   if(!num)throw std::runtime_error("nonprogressing bundle planner");offsets.push_back(ordered.size());
  }
  if(consumed!=n)throw std::runtime_error("planner coverage");ids=std::move(ordered);
 }else for(int i=k;i<n;i+=k)offsets.push_back(i);
 if(offsets.back()!=uint32_t(n))offsets.push_back(n);
 // CPU exact bijection check; actual GPU execution receives separate output qualification.
 std::vector<unsigned char> seen(n,0);for(auto t:ids){if(t>=uint32_t(n)||seen[t]++)throw std::runtime_error("tile permutation is not bijective");}
 schedule_bundle_count=int(offsets.size())-1;schedule_stats.bundles=schedule_bundle_count;
 schedule_stats.cpu_plan_ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count();
 ck(cudaMemcpy(schedule_ids,ids.data(),n*4,cudaMemcpyHostToDevice));ck(cudaMemcpy(schedule_offsets,offsets.data(),offsets.size()*4,cudaMemcpyHostToDevice));ck(cudaMemset(schedule_counter,0,4));
}
