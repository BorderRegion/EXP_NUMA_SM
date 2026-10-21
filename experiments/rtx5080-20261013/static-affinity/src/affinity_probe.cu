#include <cuda_runtime.h>
#include <cstdint>
#include <algorithm>
#include <chrono>
#include <fstream>
#include <iostream>
#include <numeric>
#include <random>
#include <stdexcept>
#include <vector>
#include <filesystem>
using Clock=std::chrono::steady_clock;
static void ck(cudaError_t e){if(e!=cudaSuccess)throw std::runtime_error(cudaGetErrorString(e));}
__device__ unsigned smid(){unsigned v;asm("mov.u32 %0, %%smid;":"=r"(v));return v;}
__host__ __device__ uint32_t mix(uint32_t x){x^=x>>16;x*=0x7feb352du;x^=x>>15;x*=0x846ca68bu;return x^(x>>16);}
struct Sample{uint64_t ticks;uint32_t checksum,sm_begin,sm_end,region,slot,block,first,reference;};
static_assert(sizeof(Sample)==40);
__global__ void initialize(uint32_t* pool,uint32_t words,uint32_t width,uint32_t stride){uint32_t i=blockIdx.x*blockDim.x+threadIdx.x;if(i<words){uint32_t region=i/stride,x=i%stride;pool[i]=(1664525u*x+((mix(region+17)|1u)))&(width-1);}}
__global__ void touch(const uint32_t* pool,uint32_t words,uint32_t* result){uint32_t sum=0;for(uint32_t i=blockIdx.x*blockDim.x+threadIdx.x;i<words;i+=gridDim.x*blockDim.x)sum+=pool[i];result[blockIdx.x*blockDim.x+threadIdx.x]=sum;}
template<int RECIPE> __global__ void probe(const uint32_t* pool,uint32_t width,uint32_t stride,const uint32_t* order,int regions,int visits,int steps,int active,Sample* out){
    int lane=threadIdx.x;int at=0;
    for(int slot=0;slot<visits+(visits+7)/8;slot++){
        bool ref=slot%9==8||(visits%8&&slot==visits+(visits+7)/8-1);int rank=slot-slot/9;uint32_t region=ref?0:order[(rank+mix(blockIdx.x+17u))%regions];
        uint32_t x=mix(region*31337u+lane*7919u+97u)&(width-1),first=x;
        unsigned s=smid();uint64_t begin=clock64();
        if(lane<active)for(int j=0;j<steps;j++){
            if constexpr(RECIPE==1){uint32_t y;asm volatile("ld.global.cg.u32 %0, [%1];":"=r"(y):"l"(pool+size_t(region)*stride+x):"memory");x=y;}
            else if constexpr(RECIPE==0)x=pool[size_t(region)*stride+x];
            else{x=(1664525u*x+(mix(region+17)|1u))&(width-1);asm volatile("" : "+r"(x));}
        }
        uint64_t ticks=clock64()-begin;unsigned end=smid();uint32_t sum=lane<active?x:0;
        for(int offset=16;offset;offset/=2)sum+=__shfl_down_sync(0xffffffffu,sum,offset);
        if(lane==0)out[blockIdx.x*(visits+(visits+7)/8)+at]={ticks,sum,s,end,region,(uint32_t)slot,blockIdx.x,first,(uint32_t)ref};
        at++;
    }
}
static uint32_t expected(int region,uint32_t width,int steps,int active){uint32_t sum=0;for(int lane=0;lane<active;lane++){uint32_t x=mix(region*31337u+lane*7919u+97u)&(width-1);for(int j=0;j<steps;j++)x=(1664525u*x+(mix(region+17)|1u))&(width-1);sum+=x;}return sum;}
int main(int argc,char**argv){try{
    if(argc!=4)throw std::runtime_error("probe out_dir epoch mode(smoke/scout/main)");std::string dir=argv[1],mode=argv[3];int epoch=std::stoi(argv[2]);bool small=mode.rfind("smoke",0)==0;std::filesystem::create_directories(dir);
    cudaDeviceProp p;ck(cudaGetDeviceProperties(&p,0));size_t poolBytes=small?1048576ull:4ull*p.l2CacheSize,evictBytes=small?1048576ull:3ull*p.l2CacheSize,padBytes=(epoch+1)*1048576ull;
    size_t free,total;ck(cudaMemGetInfo(&free,&total));if(poolBytes+evictBytes+padBytes+(8<<20)>(512ull<<20)||free<poolBytes+evictBytes+padBytes+(2ull<<30))throw std::runtime_error("memory guard");
    uint32_t *pool,*scratch,*order,*sink;void* pad;Sample* output;ck(cudaMalloc(&pad,padBytes));ck(cudaMalloc(&pool,poolBytes));ck(cudaMalloc(&scratch,evictBytes));ck(cudaMalloc(&order,256));ck(cudaMalloc(&sink,1048576));ck(cudaMalloc(&output,p.multiProcessorCount*16*72*sizeof(Sample)));
    ck(cudaMemset(scratch,0x35,evictBytes));cudaEvent_t begin,end;ck(cudaEventCreate(&begin));ck(cudaEventCreate(&end));
    std::ofstream samples(dir+"/samples.bin",std::ios::binary),dispatch(dir+"/dispatches.csv"),alloc(dir+"/allocation.json");
    alloc<<"{\"epoch\":"<<epoch<<",\"pool_bytes\":"<<poolBytes<<",\"eviction_bytes\":"<<evictBytes<<",\"padding_bytes\":"<<padBytes<<",\"virtual_base\":\""<<pool<<"\",\"sm_count\":"<<p.multiProcessorCount<<",\"l2_bytes\":"<<p.l2CacheSize<<",\"logical_content_recipe\":\"runtime initialized per-region full-period affine permutation\"}\n";
    dispatch<<"dispatch,epoch,pool_span_bytes,window_bytes,stride_bytes,recipe,active_lanes,grid_blocks,cache,round,order_seed,steps,gpu_ms,primer_ms,sample_offset,sample_count,errors\n";
    std::vector<int> spans=(mode=="main"||mode=="pressure"||mode=="atlas")?std::vector<int>{p.l2CacheSize/4,p.l2CacheSize,p.l2CacheSize*4}:std::vector<int>{small?1048576:134217728};
    int id=0;uint64_t offset=0;float maxms=0;double initms=0;
    for(int span:spans){int regions=small?8:64;uint32_t stride=span/4/regions;
      std::vector<uint32_t> widths=mode=="scout"?std::vector<uint32_t>{1024,16384,524288}:std::vector<uint32_t>{stride};
      for(uint32_t width:widths){auto initStart=Clock::now();initialize<<<(span/4+255)/256,256>>>(pool,span/4,width,stride);ck(cudaDeviceSynchronize());initms+=std::chrono::duration<double,std::milli>(Clock::now()-initStart).count();
        int rounds=(mode=="main"||mode=="pressure"||mode=="atlas")?6:2;int steps=small?16:mode=="pressure"?512:64;int visits=mode=="pressure"?8:regions;
        struct Case{int recipe,active,cache,round,sampling;};std::vector<Case> cases;
        for(int round=0;round<rounds;round++){std::vector<Case> within;for(int sampling=0;sampling<(mode=="atlas"?2:1);sampling++)for(int recipe=0;recipe<3;recipe++)for(int active:{1,32})for(int cache=0;cache<3;cache++)within.push_back({recipe,active,cache,round,sampling});std::mt19937 shuffle(2026101301u+epoch+span+width+round*7919);std::shuffle(within.begin(),within.end(),shuffle);cases.insert(cases.end(),within.begin(),within.end());}
        for(auto c:cases){bool pressure=mode=="pressure"||mode=="smoke_pressure"||c.sampling;steps=small?16:pressure?512:64;visits=pressure?4:regions;int blocks=small?8:p.multiProcessorCount*(pressure?16:(c.active==1?2:4));uint32_t seed=2026101301u+epoch*1000+c.round*71+c.cache*13+c.active+c.recipe*7;
          std::vector<uint32_t> hostOrder(regions);std::iota(hostOrder.begin(),hostOrder.end(),0);std::mt19937 rng(seed);std::shuffle(hostOrder.begin(),hostOrder.end(),rng);ck(cudaMemcpy(order,hostOrder.data(),regions*4,cudaMemcpyHostToDevice));
          float primer=0;if(c.cache){ck(cudaEventRecord(begin));touch<<<1024,256>>>(c.cache==1?pool:scratch,c.cache==1?span/4:evictBytes/4,sink);ck(cudaEventRecord(end));ck(cudaEventSynchronize(end));ck(cudaEventElapsedTime(&primer,begin,end));if(primer>20)throw std::runtime_error("primer exceeds planning limit");}
          int count=blocks*(visits+(visits+7)/8);ck(cudaEventRecord(begin));
          if(c.recipe==0)probe<0><<<blocks,32>>>(pool,width,stride,order,regions,visits,steps,c.active,output);
          if(c.recipe==1)probe<1><<<blocks,32>>>(pool,width,stride,order,regions,visits,steps,c.active,output);
          if(c.recipe==2)probe<2><<<blocks,32>>>(pool,width,stride,order,regions,visits,steps,c.active,output);
          ck(cudaGetLastError());ck(cudaEventRecord(end));ck(cudaEventSynchronize(end));float ms;ck(cudaEventElapsedTime(&ms,begin,end));maxms=std::max(maxms,ms);
          std::vector<Sample> host(count);ck(cudaMemcpy(host.data(),output,count*sizeof(Sample),cudaMemcpyDeviceToHost));std::vector<uint32_t> answers(regions);for(int r=0;r<regions;r++)answers[r]=expected(r,width,steps,c.active);int errors=0;
          for(auto&s:host)errors+=(s.region>=regions||s.checksum!=answers[s.region]||s.first!=(mix(s.region*31337u+97u)&(width-1)));
          samples.write((char*)host.data(),host.size()*sizeof(Sample));dispatch<<id++<<','<<epoch<<','<<span<<','<<width*4<<','<<stride*4<<','<<c.recipe<<','<<c.active<<','<<blocks<<','<<c.cache<<','<<c.round<<','<<seed<<','<<steps<<','<<ms<<','<<primer<<','<<offset<<','<<count<<','<<errors<<'\n';offset+=count;
          if(errors)throw std::runtime_error("CPU checksum mismatch");if(ms>20)throw std::runtime_error("kernel exceeds planning limit");
        }
      }
    }
    std::cout<<"{\"dispatches\":"<<id<<",\"samples\":"<<offset<<",\"max_kernel_ms\":"<<maxms<<",\"init_ms\":"<<initms<<",\"errors\":0}\n";
    ck(cudaFree(output));ck(cudaFree(sink));ck(cudaFree(order));ck(cudaFree(scratch));ck(cudaFree(pool));ck(cudaFree(pad));return 0;
}catch(std::exception&e){std::cerr<<"ERROR: "<<e.what()<<'\n';return 2;}}
