
#include <cstdlib>
#include <new>
#include <cstdio>
#include <cmath>
static bool tracking=false;static size_t allocs=0;
extern "C" void* __libc_malloc(size_t);
extern "C" void* __libc_calloc(size_t,size_t);
extern "C" void* __libc_realloc(void*,size_t);
extern "C" void* malloc(size_t n)noexcept{if(tracking)++allocs;return __libc_malloc(n);}
extern "C" void* calloc(size_t a,size_t b)noexcept{if(tracking)++allocs;return __libc_calloc(a,b);}
extern "C" void* realloc(void*p,size_t n)noexcept{if(tracking)++allocs;return __libc_realloc(p,n);}
#include "policy.hpp"
int main(){int shapes[][3]={{2,2048,6144},{2,2048,12288},{2,2048,24576},{2,6144,6144},{2,6144,12288},{2,6144,24576},{12,2048,6144},{12,2048,12288},{12,2048,24576},{12,6144,6144},{12,6144,12288},{12,6144,24576},{48,2048,6144},{48,2048,12288},{48,2048,24576},{48,6144,6144},{48,6144,12288},{48,6144,24576},{192,2048,6144},{192,2048,12288},{192,2048,24576},{192,6144,6144},{192,6144,12288},{192,6144,24576},{6,2560,10240},{6,2560,20480},{6,7168,10240},{6,7168,20480},{20,2560,10240},{20,2560,20480},{20,7168,10240},{20,7168,20480},{72,2560,10240},{72,2560,20480},{72,7168,10240},{72,7168,20480},{224,2560,10240},{224,2560,20480},{224,7168,10240},{224,7168,20480},{1,1024,16384},{1,8192,4096},{8,1024,16384},{8,8192,16384},{32,8192,4096},{128,4096,4096},{512,1024,16384},{3,11008,8192},{1024,3072,8192},{24,16384,8192},{24,3072,2048},{4,3072,40960}};int hs[]={0,1,32,256,1024,4096};size_t calls=0;volatile double sink=0;double out[13];
 for(auto&x:shapes)for(int p=0;p<5;p++)for(int h:hs)for(int d=0;d<2;d++){sr_export_choice(x[0],x[1],x[2],p,h,out,d);sink+=out[1];}
 tracking=true;
 for(int repeat=0;repeat<10;repeat++)for(auto&x:shapes)for(int p=0;p<5;p++)for(int h:hs)for(int d=0;d<2;d++){sr_export_choice(x[0],x[1],x[2],p,h,out,d);sink+=out[1]+out[12];calls++;}
 tracking=false;printf("{\"status\":\"%s\",\"calls\":%zu,\"malloc_calloc_realloc_calls\":%zu,\"sink\":%.17g}\n",allocs?"FAIL":"PASS",calls,allocs,double(sink));return allocs?1:0;
}
