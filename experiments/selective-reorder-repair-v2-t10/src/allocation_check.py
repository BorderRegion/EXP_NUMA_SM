from common import *
import subprocess
cases=read(INPUT/'plans/cases.json');arr=','.join('{'+','.join(str(c[k]) for k in ['M','N','K'])+'}' for c in cases)
source=r'''
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
int main(){int shapes[][3]={CASES};int hs[]={0,1,32,256,1024,4096};size_t calls=0;volatile double sink=0;double out[13];
 for(auto&x:shapes)for(int p=0;p<5;p++)for(int h:hs)for(int d=0;d<2;d++){sr_export_choice(x[0],x[1],x[2],p,h,out,d);sink+=out[1];}
 tracking=true;
 for(int repeat=0;repeat<10;repeat++)for(auto&x:shapes)for(int p=0;p<5;p++)for(int h:hs)for(int d=0;d<2;d++){sr_export_choice(x[0],x[1],x[2],p,h,out,d);sink+=out[1]+out[12];calls++;}
 tracking=false;printf("{\"status\":\"%s\",\"calls\":%zu,\"malloc_calloc_realloc_calls\":%zu,\"sink\":%.17g}\n",allocs?"FAIL":"PASS",calls,allocs,double(sink));return allocs?1:0;
}
'''.replace('CASES',arr)
(ROOT/'support/allocation_check.cpp').write_text(source)
subprocess.run(['g++','-std=c++17','-O3','-I'+str(ROOT/'src'),str(ROOT/'support/allocation_check.cpp'),'-o',str(ROOT/'build/allocation_check')],check=True)
p=subprocess.run([str(ROOT/'build/allocation_check')],capture_output=True,text=True);(ROOT/'reports/NEW_ALLOCATOR_CHECK.json').write_text(p.stdout);assert p.returncode==0,p.stderr;print(p.stdout)
